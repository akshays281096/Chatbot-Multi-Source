"""
CSV and Excel file handler service
Based on excel_agent.py CSVHandler pattern
Handles data processing without RAG pipeline for tabular data
"""
import pandas as pd
import logging
import os
from typing import Dict, List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class CSVExcelHandler:
    """Handler for CSV and Excel files without RAG pipeline"""
    
    def __init__(self, file_path: str):
        """
        Initialize the handler.
        
        Args:
            file_path: Path to the CSV or Excel file
        """
        self.file_path = file_path
        self.dfs: Dict[str, pd.DataFrame] = {}
        self.current_sheet = None
        self.file_type = None
        
    def preprocess_sheet(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess a dataframe to clean and prepare it for analysis.
        Based on excel_agent.py CSVHandler.preprocess_sheet
        
        Args:
            df: The dataframe to preprocess
            
        Returns:
            The preprocessed dataframe
        """
        # Remove completely empty rows
        df = df[~df.apply(lambda row: all(pd.isna(val) or str(val).strip() == '' for val in row), axis=1)]
        
        # Remove columns where more than 50% of the values are empty
        cols_to_keep_final = [
            col for col in df.columns
            if self.count_valid(df[col]) > self.count_invalid(df[col])
        ]
        
        df = df[cols_to_keep_final]
        
        # Remove rows until a valid header is found
        while len(df) > 0:
            if any(str(col).startswith('Unnamed') or str(col).isspace() or str(col) == '' for col in df.columns):
                new_columns = [
                    f'Unnamed: {i}' if pd.isna(val) or str(val).isspace() or str(val) == '' else str(val).strip()
                    for i, val in enumerate(df.iloc[0])
                ]
                df.columns = new_columns
                df = df.iloc[1:].reset_index(drop=True)
            else:
                break
        
        # Remove rows where all values are the same as the column names
        df = df[~df.apply(lambda row: all(str(row[col]).strip() == str(col).strip() for col in df.columns), axis=1)]
        
        return df
    
    @staticmethod
    def count_valid(col: pd.Series) -> int:
        """
        Count valid (non-empty) values in a column.
        
        Args:
            col: The column to check
            
        Returns:
            Count of valid values
        """
        return col.apply(lambda x: pd.notna(x) and str(x).strip() != '').sum()
    
    @staticmethod
    def count_invalid(col: pd.Series) -> int:
        """
        Count invalid (empty) values in a column.
        
        Args:
            col: The column to check
            
        Returns:
            Count of invalid values
        """
        return col.apply(lambda x: pd.isna(x) or str(x).strip() == '').sum()
    
    def load_and_preprocess_data(self) -> pd.DataFrame:
        """
        Load and preprocess data from the file path.
        Based on excel_agent.py CSVHandler.load_and_preprocess_data
        
        Returns:
            The current dataframe after loading
        """
        if self.file_path.endswith('.csv'):
            self.file_type = 'csv'
            try:
                # Try multiple encodings
                for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                    try:
                        df = pd.read_csv(self.file_path, encoding=encoding, encoding_errors="ignore")
                        break
                    except:
                        continue
                if df is None:
                    raise ValueError("Could not read CSV with any encoding")
            except Exception as e:
                logger.error(f"Error reading CSV {self.file_path}: {e}")
                raise
            
            self.dfs['default'] = self.preprocess_sheet(df)
            self.current_sheet = 'default'
            
        elif self.file_path.endswith(('.xls', '.xlsx')):
            self.file_type = 'excel'
            try:
                excel_file = pd.ExcelFile(self.file_path)
                for sheet_name in excel_file.sheet_names:
                    try:
                        if self.file_path.endswith('.xlsx'):
                            df = pd.read_excel(self.file_path, sheet_name=sheet_name, engine='openpyxl')
                        else:
                            df = pd.read_excel(self.file_path, sheet_name=sheet_name, engine='xlrd')
                    except Exception as e:
                        logger.warning(f"Error reading sheet '{sheet_name}': {e}, trying with openpyxl")
                        try:
                            df = pd.read_excel(self.file_path, sheet_name=sheet_name, engine='openpyxl')
                        except:
                            logger.warning(f"Failed to read sheet '{sheet_name}'")
                            continue
                    
                    processed_df = self.preprocess_sheet(df)
                    if not processed_df.empty:
                        self.dfs[sheet_name] = processed_df
                
                if self.dfs:
                    self.current_sheet = next(iter(self.dfs))
                else:
                    raise ValueError("No valid data found in any sheet")
            except Exception as e:
                logger.error(f"Error reading Excel {self.file_path}: {e}")
                raise
        else:
            raise ValueError("Unsupported file type. Only CSV, XLS, and XLSX files are supported.")
        
        return self.get_current_df()
    
    def get_current_df(self) -> pd.DataFrame:
        """
        Get the current dataframe.
        
        Returns:
            The current dataframe
        """
        if not self.dfs:
            raise ValueError("No data loaded. Call load_and_preprocess_data first.")
        return self.dfs[self.current_sheet]
    
    def list_sheets(self) -> List[str]:
        """
        List all available sheets.
        
        Returns:
            List of sheet names
        """
        return list(self.dfs.keys())
    
    def switch_sheet(self, sheet_name: str) -> pd.DataFrame:
        """
        Switch to a different sheet.
        
        Args:
            sheet_name: The name of the sheet to switch to
            
        Returns:
            The dataframe for the selected sheet
        """
        if sheet_name not in self.dfs:
            raise ValueError(f"Sheet '{sheet_name}' not found. Available sheets: {self.list_sheets()}")
        self.current_sheet = sheet_name
        return self.get_current_df()
    
    def calculate_sheet_relevance(self, query: str, sheet_name: str) -> float:
        """
        Calculate the relevance of a sheet to a query.
        Based on excel_agent.py CSVHandler.calculate_sheet_relevance
        
        Args:
            query: The query to check relevance against
            sheet_name: The name of the sheet to check
            
        Returns:
            Relevance score
        """
        df = self.dfs[sheet_name]
        headers = ' '.join(df.columns.astype(str))
        sample_data = ' '.join(df.head(10).astype(str).values.flatten())
        sheet_name_text = sheet_name.replace("_", " ").replace("-", " ")
        
        # Give more weight to headers and sheet name
        text = (sheet_name_text + " ") * 3 + (headers + " ") * 2 + sample_data
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        
        try:
            tfidf_matrix = vectorizer.fit_transform([text, query])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Also boost score if query words appear in sheet name
            if any(word in sheet_name_text.lower() for word in query.lower().split()):
                similarity += 0.15
            
            return float(similarity)
        except Exception as e:
            logger.warning(f"Error calculating sheet relevance: {e}")
            return 0.0
    
    def find_most_relevant_sheet(self, query: str) -> str:
        """
        Find the most relevant sheet for a query.
        Based on excel_agent.py CSVHandler.find_most_relevant_sheet
        
        Args:
            query: The query to find the most relevant sheet for
            
        Returns:
            The name of the most relevant sheet
        """
        if len(self.dfs) == 1:
            return next(iter(self.dfs))
        
        relevance_scores = {
            sheet: self.calculate_sheet_relevance(query, sheet)
            for sheet in self.dfs.keys()
        }
        most_relevant_sheet = max(relevance_scores.items(), key=lambda x: x[1])
        return most_relevant_sheet[0]
    
    def find_most_relevant_sheets(self, query: str, top_n: int = 3) -> List[str]:
        """
        Find the most relevant sheets for a query.
        Based on excel_agent.py CSVHandler.find_most_relevant_sheets
        
        Args:
            query: The query to find relevant sheets for
            top_n: Number of top sheets to return
            
        Returns:
            List of the most relevant sheet names
        """
        if len(self.dfs) == 1:
            return [next(iter(self.dfs))]
        
        relevance_scores = {
            sheet: self.calculate_sheet_relevance(query, sheet)
            for sheet in self.dfs.keys()
        }
        sorted_sheets = sorted(relevance_scores.items(), key=lambda x: x[1], reverse=True)
        return [sheet for sheet, _ in sorted_sheets[:top_n]]
    
    @staticmethod
    def sanitize_for_json(df: pd.DataFrame) -> List[Dict]:
        """
        Convert dataframe to list of dicts, handling NaN and inf values.
        Replaces NaN with None and inf values with string representations.
        
        Args:
            df: The dataframe to convert
            
        Returns:
            List of dictionaries safe for JSON serialization
        """
        records = []
        for _, row in df.iterrows():
            record = {}
            for col, value in row.items():
                if pd.isna(value):
                    record[col] = None
                elif isinstance(value, float):
                    if value == float('inf'):
                        record[col] = "inf"
                    elif value == float('-inf'):
                        record[col] = "-inf"
                    else:
                        record[col] = value
                else:
                    record[col] = value
            records.append(record)
        return records
