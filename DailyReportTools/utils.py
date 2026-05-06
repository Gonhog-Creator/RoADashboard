"""
Shared utilities module for RoADashboard
Contains common functions used across multiple modules to eliminate code duplication
"""

import streamlit as st
import pandas as pd
from datetime import datetime


def calculate_daily_rate(df_or_values, dates_or_column, threshold=0):
    """
    Calculate true daily rate based on time differences between reports
    
    Supports multiple calling patterns:
    1. calculate_daily_rate(sorted_df, value_column) - for DataFrame with date column
    2. calculate_daily_rate(values, dates) - for raw values and dates lists
    
    Args:
        df_or_values: DataFrame or list of values
        dates_or_column: Column name (if DataFrame) or list of dates (if values list)
        threshold: Minimum time difference in days to calculate rate
    
    Returns:
        List or Series of daily rates
    """
    # Check if first argument is a DataFrame (most common usage)
    if isinstance(df_or_values, pd.DataFrame):
        sorted_df = df_or_values
        value_column = dates_or_column
        
        if len(sorted_df) < 2:
            return pd.Series([0] * len(sorted_df))
        
        daily_rates = []
        for i in range(len(sorted_df)):
            if i == 0:
                daily_rates.append(0)
            else:
                current_value = sorted_df.iloc[i][value_column]
                previous_value = sorted_df.iloc[i-1][value_column]
                current_time = sorted_df.iloc[i]['date']
                previous_time = sorted_df.iloc[i-1]['date']
                
                # Calculate time difference in days
                time_diff = (current_time - previous_time).total_seconds() / (24 * 3600)
                
                if time_diff > threshold:
                    change = current_value - previous_value
                    daily_rate = change / time_diff
                    daily_rates.append(daily_rate)
                else:
                    daily_rates.append(0)
        
        return pd.Series(daily_rates)
    
    # Handle list input (values, dates)
    else:
        values = df_or_values
        dates = dates_or_column
        
        if len(values) < 2:
            return [0] * len(values)
        
        daily_rates = []
        for i in range(len(values)):
            if i == 0:
                daily_rates.append(0)
            else:
                current_value = values[i]
                previous_value = values[i-1]
                current_time = dates[i]
                previous_time = dates[i-1]
                
                # Calculate time difference in days
                time_diff = (current_time - previous_time).total_seconds() / (24 * 3600)
                
                if time_diff > threshold:
                    change = current_value - previous_value
                    daily_rate = change / time_diff
                    daily_rates.append(daily_rate)
                else:
                    daily_rates.append(0)
        
        return daily_rates


def format_number(num, show_full=False):
    """
    Format numbers with optional full display
    
    Args:
        num: Number to format
        show_full: If True, show full number with commas; if False, use abbreviations
    
    Returns:
        Formatted string
    """
    # Handle NaN values
    if pd.isna(num):
        return "N/A"
    
    if show_full:
        # Full numbers with comma separators
        return f"{int(num):,}"
    else:
        # Abbreviated numbers - handle negative numbers properly
        abs_num = abs(num)
        sign = "-" if num < 0 else ""
        
        if abs_num >= 1_000_000_000:
            return f"{sign}{abs_num/1_000_000_000:.1f}B"
        elif abs_num >= 1_000_000:
            return f"{sign}{abs_num/1_000_000:.1f}M"
        elif abs_num >= 1_000:
            return f"{sign}{abs_num/1_000:.1f}K"
        else:
            return f"{sign}{int(abs_num)}"


def format_change(change):
    """
    Format change numbers with sign
    
    Args:
        change: Numeric change value
        
    Returns:
        Formatted string with sign
    """
    if pd.isna(change):
        return "N/A"
    sign = "+" if change >= 0 else ""
    return f"{sign}{format_number(change)}"


def format_rate(rate, show_full=False):
    """
    Format rate numbers with appropriate units
    
    Args:
        rate: Daily rate value
        show_full: Whether to show full numbers
        
    Returns:
        Formatted rate string
    """
    if pd.isna(rate) or rate == 0:
        return "0/day"
    
    if show_full:
        return f"{int(rate):,}/day"
    else:
        return f"{format_number(rate)}/day"


def safe_divide(numerator, denominator, default=0):
    """
    Safely divide two numbers, returning default if division by zero
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if denominator is zero
        
    Returns:
        Division result or default
    """
    try:
        if denominator == 0 or pd.isna(denominator):
            return default
        return numerator / denominator
    except:
        return default


def calculate_percentage(part, whole, default=0):
    """
    Calculate percentage safely
    
    Args:
        part: Part value
        whole: Whole value
        default: Default if whole is zero
        
    Returns:
        Percentage value
    """
    return safe_divide(part * 100, whole, default)


def get_realm_name(realm_id):
    """
    Convert realm ID to realm name
    
    Args:
        realm_id: Realm ID
        
    Returns:
        Realm name string
    """
    realm_names = {
        1: "Ruby",
        2: "Sapphire", 
        3: "Emerald",
        4: "Diamond"
    }
    return realm_names.get(realm_id, "Ruby")
