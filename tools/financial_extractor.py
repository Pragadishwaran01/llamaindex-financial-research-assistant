import re
from typing import Dict, List, Optional
from llama_index.core.tools import FunctionTool

class FinancialMetricsExtractor:
    @staticmethod
    def extract_metrics(text: str) -> Dict[str, any]:
        metrics = {
            "currencies": [],
            "percentages": [],
            "yoy_changes": [],
            "segments": [],
            "normalized_values": {},
            "missing_data": [],
            "extraction_confidence": 0.0
        }
        
        currency_pattern = r'\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*([BMK])?'
        currencies = re.findall(currency_pattern, text)
        for amount, unit in currencies:
            value = float(amount.replace(',', ''))
            original = f"${amount}{unit or ''}"
            if unit == 'B':
                value *= 1_000_000_000
            elif unit == 'M':
                value *= 1_000_000
            elif unit == 'K':
                value *= 1_000
            metrics["currencies"].append({
                "original": original,
                "normalized_value": value,
                "unit": "USD"
            })
        
        percentage_pattern = r'(\d+(?:\.\d+)?)\s*%'
        percentages = re.findall(percentage_pattern, text)
        metrics["percentages"] = [{"value": float(p), "unit": "%"} for p in percentages]
        
        yoy_patterns = [
            r'(?:YoY|year[- ]over[- ]year|y/y)\s*(?:change|growth|increase|decrease)?\s*(?:of)?\s*([+-]?\d+(?:\.\d+)?)\s*%',
            r'([+-]?\d+(?:\.\d+)?)\s*%\s*(?:YoY|year[- ]over[- ]year)',
            r'(?:increased|decreased|changed)\s+(?:by\s+)?([+-]?\d+(?:\.\d+)?)\s*%'
        ]
        for pattern in yoy_patterns:
            yoy_changes = re.findall(pattern, text, re.IGNORECASE)
            for change in yoy_changes:
                metrics["yoy_changes"].append({
                    "value": float(change),
                    "unit": "%",
                    "type": "year_over_year"
                })
        
        segment_keywords = {
            'Aerospace': ['Aerospace', 'Aero'],
            'HBT': ['HBT', 'Building Technologies', 'Honeywell Building'],
            'PMT': ['PMT', 'Performance Materials', 'Performance Materials and Technologies'],
            'SPS': ['SPS', 'Safety and Productivity', 'Safety and Productivity Solutions']
        }
        for segment_key, keywords in segment_keywords.items():
            if any(keyword in text for keyword in keywords):
                metrics["segments"].append(segment_key)
        
        total_found = len(metrics["currencies"]) + len(metrics["percentages"]) + len(metrics["yoy_changes"])
        metrics["extraction_confidence"] = min(total_found / 5.0, 1.0)
        
        if not metrics["currencies"]:
            metrics["missing_data"].append("No currency values found")
        if not metrics["percentages"]:
            metrics["missing_data"].append("No percentages found")
        
        return metrics
    
    @staticmethod
    def parse_financial_table(text: str, segment: str) -> Optional[Dict]:
        result = {
            "segment": segment,
            "revenue_2023": None,
            "revenue_2022": None,
            "profit_2023": None,
            "profit_2022": None,
            "margin_2023": None,
            "margin_2022": None
        }
        
        segment_section = re.search(f'{segment}.*?(?=\n\n|\\Z)', text, re.DOTALL | re.IGNORECASE)
        if segment_section:
            section_text = segment_section.group(0)
            
            revenue_match = re.search(r'revenue.*?\$\s*(\d+(?:,\d{3})*)', section_text, re.IGNORECASE)
            if revenue_match:
                result["revenue_2023"] = float(revenue_match.group(1).replace(',', ''))
            
            margin_match = re.search(r'(?:profit\s+)?margin.*?(\d+(?:\.\d+)?)\s*%', section_text, re.IGNORECASE)
            if margin_match:
                result["margin_2023"] = float(margin_match.group(1))
        
        return result if any(v is not None for k, v in result.items() if k != "segment") else None

def create_financial_extractor_tool() -> FunctionTool:
    extractor = FinancialMetricsExtractor()
    
    def extract_financial_metrics(text: str) -> str:
        return str(extractor.extract_metrics(text))
    
    return FunctionTool.from_defaults(
        fn=extract_financial_metrics,
        name="financial_metrics_extractor",
        description="Extracts financial data including currencies, percentages, YoY changes, and segments"
    )
