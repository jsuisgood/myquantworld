from data_fetching.tushare_adapter import TuShareClient

print("Testing TuShareClient initialization...")
try:
    # Initialize client without token to test fallback mechanism
    client = TuShareClient()
    print("Successfully initialized TuShareClient")
    
    # Test getting stock basic info (should return mock data)
    basic_info = client._get_stock_basic_info_impl()
    print(f"\nGot stock basic info (rows: {len(basic_info)})")
    print(basic_info.head())
    
    # Test getting daily data for a stock (should return mock data)
    daily_data = client._get_stock_daily_data_impl('000001', '20230101', '20230110')
    print(f"\nGot daily data (rows: {len(daily_data)})")
    print(daily_data.head())
    
    print("\nTest completed successfully!")
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")