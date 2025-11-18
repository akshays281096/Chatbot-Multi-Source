"""
LangGraph service for orchestrating the chatbot workflow
Implemented based on weam/nodejs and gocustomai/backend_python patterns
"""
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from typing import Literal, List, Dict, Any, Optional
import logging
import pandas as pd
from app.services.llm_factory import LLMFactory
from app.services.web_scraper import scrape_web_page
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


# Web scraping tool - matches weam pattern
@tool
def web_scrape_tool(url: str) -> str:
    """Scrape a web page and return its content. Use this when you need to fetch information from a URL.
    
    Args:
        url: The URL of the web page to scrape
        
    Returns:
        A string containing the scraped content from the web page
    """
    try:
        page_data = scrape_web_page(url)
        return f"Title: {page_data.get('title', 'N/A')}\n\nContent: {page_data.get('text', '')[:2000]}"
    except Exception as e:
        return f"Error scraping URL {url}: {str(e)}"


# Global state references (set during graph creation)
_current_vector_store: Optional[VectorStore] = None
_current_llm_provider: Literal["OPENAI", "ANTHROPIC", "GEMINI"] = "OPENAI"
_current_model: str = "gpt-4o-mini"
_current_llm = None
_current_llm_with_tools = None
_current_tools = None
_current_tool_node = None
_current_dataframes: Dict[str, pd.DataFrame] = {}  # Store dataframes for CSV/Excel files


def data_query_tool(query_code: str, dataframe_name: str = "df") -> str:
    """
    Execute a pandas query on uploaded CSV/Excel data.
    Use this tool when you need to perform calculations or analysis on structured data.
    
    The tool has access to the following dataframes:
    - df: Main dataframe (if single CSV/Excel file is selected)
    - Or access specific dataframes by name: df_filename_sheetname
    
    Args:
        query_code: Python pandas query code to execute (e.g., "df[df['Department'] == 'Sales']['Salary'].sum()")
        dataframe_name: Name of the dataframe variable to use (default: "df")
        
    Returns:
        String representation of the query result
    """
    try:
        # Get the dataframe(s)
        if not _current_dataframes:
            return "Error: No CSV/Excel data available. Please upload CSV or Excel files."
        
        # If only one dataframe, make it available as 'df'
        namespace = {}
        if len(_current_dataframes) == 1:
            namespace['df'] = list(_current_dataframes.values())[0]
        
        # Make all dataframes available by their keys
        namespace.update(_current_dataframes)
        
        # Add common pandas functions to namespace
        namespace['pd'] = pd
        namespace['sum'] = sum
        namespace['len'] = len
        namespace['max'] = max
        namespace['min'] = min
        namespace['str'] = str
        
        # Execute the query
        result = eval(query_code, {"__builtins__": {}}, namespace)
        
        # Convert result to string
        if isinstance(result, pd.DataFrame):
            return result.to_string()
        elif isinstance(result, pd.Series):
            return result.to_string()
        else:
            return str(result)
            
    except Exception as e:
        return f"Error executing query: {str(e)}\nQuery code: {query_code}"


def should_continue(state: MessagesState) -> Literal["tools", "end"]:
    """Determine if we should continue to tools or end - matches gocustomai pattern"""
    messages = state["messages"]
    last_message = messages[-1]
    
    # Check for tool_calls
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return "end"


async def call_model(state: MessagesState):
    """Call the LLM model - matches gocustomai chatbot pattern"""
    try:
        messages = state["messages"]
        
        # Use the pre-configured LLM with tools
        if _current_llm_with_tools:
            response = await _current_llm_with_tools.ainvoke(messages)
        else:
            # Fallback to LLM without tools
            response = await _current_llm.ainvoke(messages)
        
        return {"messages": [response]}
        
    except Exception as e:
        logger.error(f"Error calling model: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


async def build_graph(
    vector_store: Optional[VectorStore] = None,
    llm_provider: Literal["OPENAI", "ANTHROPIC", "GEMINI"] = "OPENAI",
    model: str = "gpt-4o-mini",
    query: Optional[str] = None
):
    """
    Build the LangGraph workflow - matches gocustomai pattern
    RAG context is injected into system message before graph creation
    
    Args:
        vector_store: Vector store instance (optional, None if RAG is disabled)
        llm_provider: LLM provider to use
        model: Model name to use
        query: Optional query string for context
    """
    global _current_vector_store, _current_llm_provider, _current_model
    global _current_llm, _current_llm_with_tools, _current_tools, _current_tool_node
    
    # Set global references
    _current_vector_store = vector_store
    _current_llm_provider = llm_provider
    _current_model = model
    
    # Create LLM instance - matches weam pattern (default temperature=1)
    # Temperature will be adjusted automatically for models that only support 1.0
    _current_llm = LLMFactory.create_llm(
        provider=llm_provider,
        model=model,
        temperature=1.0  # Default to 1.0 like weam (opts.temperature ?? 1)
    )
    
    # Prepare tools list - matches gocustomai pattern
    _current_tools = [web_scrape_tool]
    
    # Add data_query_tool if CSV/Excel dataframes are available
    if _current_dataframes:
        # Convert data_query_tool to a langchain tool
        @tool
        def data_query(query_code: str) -> str:
            """
            Execute a pandas query on uploaded CSV/Excel data.
            Use this tool when you need to perform calculations or analysis on structured data (sum, count, average, etc.).
            
            The dataframe(s) are available as:
            - df: If a single CSV/Excel file is selected
            - Or by their names: df_filename_sheetname
            
            Example queries:
            - df[df['Department'] == 'Sales']['Salary'].sum()
            - df['Age'].mean()
            - len(df[df['Status'] == 'Active'])
            - df.groupby('Department')['Salary'].sum()
            
            Args:
                query_code: Python pandas query code to execute
                
            Returns:
                Result of the query as a string
            """
            return data_query_tool(query_code)
        
        _current_tools.append(data_query)
    
    # Bind tools to LLM - matches gocustomai pattern (line 144)
    try:
        # Check if model supports tools (some models don't)
        # For now, bind tools for all models
        _current_llm_with_tools = _current_llm.bind_tools(_current_tools)
        logger.info(f"Tools bound successfully to {llm_provider} model: {model}. Total tools: {len(_current_tools)}")
    except Exception as e:
        logger.warning(f"Failed to bind tools: {e}, using LLM without tools")
        _current_llm_with_tools = _current_llm
    
    # Create ToolNode - matches gocustomai pattern (line 135)
    _current_tool_node = ToolNode(_current_tools)
    
    # Create graph with MessagesState - matches gocustomai pattern (line 184)
    workflow = StateGraph(MessagesState)
    
    # Add nodes
    workflow.add_node("chatbot", call_model)
    workflow.add_node("tools", _current_tool_node)
    
    # Set entry point
    workflow.add_edge(START, "chatbot")
    
    # Add conditional edges - matches gocustomai pattern (line 186)
    workflow.add_conditional_edges(
        "chatbot",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    # Add edge from tools back to chatbot - matches gocustomai pattern (line 193)
    workflow.add_edge("tools", "chatbot")
    
    # Compile graph
    app = workflow.compile()
    
    return app


async def query_chatbot(
    query: str,
    vector_store: Optional[VectorStore] = None,
    llm_provider: Literal["OPENAI", "ANTHROPIC", "GEMINI"] = "OPENAI",
    model: str = "gpt-4o-mini",
    conversation_history: List[Dict] = None,
    use_rag: bool = True,
    selected_documents: Optional[List[str]] = None
) -> Dict:
    """
    Query the chatbot and get a response with references
    Matches weam and gocustomai patterns for RAG context injection
    
    Args:
        query: User query
        vector_store: Vector store instance (optional if use_rag=False)
        llm_provider: LLM provider to use
        model: Model name to use
        conversation_history: Previous conversation messages
        use_rag: Whether to use RAG pipeline (search uploaded documents)
        selected_documents: List of document IDs to use for RAG (if None, all documents are used)
    """
    
    try:
        # Load dataframes from vector store (for CSV/Excel data query tool)
        global _current_dataframes
        if vector_store:
            _current_dataframes = await vector_store.get_dataframes()
            logger.info(f"Loaded {len(_current_dataframes)} dataframes for this query")
        else:
            _current_dataframes = {}
        
        # Prepare messages BEFORE building graph - matches weam pattern
        messages = []
        
        # Add system message
        if use_rag:
            system_content = """You are a helpful AI assistant that answers questions based on uploaded documents, web pages, and other sources. Always cite your sources when providing information.

When working with CSV or Excel files (structured data):
- You have access to Python/Pandas tools to execute queries on the data
- Use the data_query tool to perform calculations (sum, count, average, etc.) directly on the data
- For structured data questions, ALWAYS use the data_query tool for accurate results
- Example: For "What is the total salary?" use: data_query("df[df['Department'] == 'Sales']['Salary'].sum()")
- For counting operations, use: data_query("len(df[df['Status'] == 'Active'])")
- For aggregations, use: data_query("df.groupby('Department')['Salary'].sum()")
- If you see table data in the context, you can analyze it or use the data_query tool for calculations"""
        else:
            system_content = "You are a helpful AI assistant that answers questions. Provide accurate and helpful responses based on your training data."
        
        # Inject RAG context into system message BEFORE graph creation - matches weam pattern (line 340-341)
        if use_rag and vector_store:
            try:
                # For CSV/Excel queries, retrieve more results to get full table data
                # Check if query might be about structured data (CSV/Excel)
                structured_data_keywords = ['count', 'sum', 'total', 'average', 'max', 'min', 'tenure', 'row', 'column', 'table', 'data']
                is_structured_query = any(keyword in query.lower() for keyword in structured_data_keywords)
                
                # Use more results for structured data queries to ensure full table is retrieved
                n_results = 10 if is_structured_query else 3
                
                # Search for relevant documents (no filter in query, will filter results if needed)
                rag_results = await vector_store.search(query, n_results=n_results)
                
                # Filter results by selected documents if specified
                if selected_documents and len(selected_documents) > 0:
                    # Parse selected_documents which are in format "source" or "source#sheet_name"
                    filtered_results = []
                    for result in rag_results:
                        metadata = result.get('metadata', {})
                        source = metadata.get('source', '')
                        sheet_name = metadata.get('sheet_name', '')
                        
                        # Check if this result matches any selected document
                        for selected_doc in selected_documents:
                            if sheet_name and '#' in selected_doc:
                                # Excel with sheet - format is "source#sheet_name"
                                selected_source, selected_sheet = selected_doc.split('#', 1)
                                if source == selected_source and sheet_name == selected_sheet:
                                    filtered_results.append(result)
                                    break
                            elif source == selected_doc:
                                # Regular document - format is just "source"
                                filtered_results.append(result)
                                break
                    
                    rag_results = filtered_results
                
                if rag_results:
                    # Build RAG context - matches weam pattern
                    rag_context = "\n\n----\nContext from uploaded documents:\n"
                    
                    # For structured data, include more text (full chunks) to preserve table structure
                    # For other documents, use shorter snippets
                    text_limit = 10000 if is_structured_query else 500
                    
                    # Group results by source to combine CSV/Excel chunks from same file
                    results_by_source = {}
                    for result in rag_results:
                        metadata = result.get('metadata', {})
                        source = metadata.get('source', 'Unknown')
                        source_type = metadata.get('source_type', 'document')
                        
                        # For CSV/Excel files, group by source to combine all chunks
                        if source_type in ['csv', 'excel']:
                            if source not in results_by_source:
                                results_by_source[source] = []
                            results_by_source[source].append(result)
                        else:
                            # For other files, add individually
                            if source not in results_by_source:
                                results_by_source[source] = []
                            results_by_source[source].append(result)
                    
                    # Build context, combining CSV/Excel chunks from same file
                    for source, source_results in results_by_source.items():
                        metadata = source_results[0].get('metadata', {})
                        source_type = metadata.get('source_type', 'document')
                        
                        if source_type in ['csv', 'excel']:
                            # Combine all chunks from the same CSV/Excel file
                            combined_text = "\n".join([r.get('text', '') for r in source_results])
                            rag_context += f"\n[From {source_type}: {source}]\n{combined_text}\n"
                        else:
                            # For other files, add each chunk separately
                            for result in source_results:
                                text = result.get('text', '')[:text_limit]
                                rag_context += f"\n[From {source_type}: {source}]\n{text}\n"
                    
                    rag_context += "\n----\nUse the above document context when relevant to answer the user's question. For CSV/Excel files, you have access to the complete table data - analyze it directly.\n"
                    
                    # Append RAG context to system message - matches weam pattern
                    system_content += rag_context
            except Exception as e:
                logger.warning(f"Failed to add RAG context: {e}")
        
        # Create system message with RAG context
        system_message = SystemMessage(content=system_content)
        messages.append(system_message)
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(AIMessage(content=msg['content']))
        
        # Add current query
        messages.append(HumanMessage(content=query))
        
        # Build graph (tools are already configured)
        # Pass vector_store only if RAG is enabled
        app = await build_graph(vector_store if use_rag else None, llm_provider, model, query)
        
        # Create initial state
        initial_state = {
            "messages": messages
        }
        
        # Run the graph
        final_state = await app.ainvoke(initial_state)
        
        # Extract response and references
        response_messages = final_state["messages"]
        ai_response = None
        references = []
        
        # Find the last AI message
        for msg in reversed(response_messages):
            if isinstance(msg, AIMessage):
                ai_response = msg.content
                break
        
        # Extract references from RAG context in system message
        for msg in response_messages:
            if isinstance(msg, SystemMessage) and "[From" in msg.content:
                import re
                sources = re.findall(r'\[From ([^\]]+)\]', msg.content)
                references.extend(sources)
        
        # Also check vector store search results for references
        if vector_store:
            try:
                search_results = await vector_store.search(query, n_results=3)
                for result in search_results:
                    metadata = result.get('metadata', {})
                    source = metadata.get('source', 'Unknown')
                    source_type = metadata.get('source_type', 'document')
                    references.append(f"{source_type}: {source}")
            except Exception as ref_error:
                logger.warning(f"Failed to get references from vector store: {ref_error}")
        
        # Deduplicate references
        references = list(set(references))
        
        return {
            "response": ai_response or "I apologize, but I couldn't generate a response.",
            "references": references,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error querying chatbot: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "response": f"Error: {str(e)}",
            "references": [],
            "status": "error"
        }
