"""
Data Generation Script for StockSense
Generates realistic sample inventory and sales data for demonstration purposes.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

def generate_product_catalog(n_products=1000):
    """Generate a realistic product catalog"""
    categories = [
        'Electronics', 'Clothing', 'Home & Garden', 'Food & Beverages',
        'Health & Beauty', 'Sports & Outdoors', 'Toys & Games', 'Automotive'
    ]
    
    subcategories = {
        'Electronics': ['Smartphones', 'Laptops', 'Headphones', 'Tablets'],
        'Clothing': ['Mens Apparel', 'Womens Apparel', 'Shoes', 'Accessories'],
        'Home & Garden': ['Furniture', 'Kitchen', 'Decor', 'Tools'],
        'Food & Beverages': ['Snacks', 'Beverages', 'Fresh Produce', 'Frozen'],
        'Health & Beauty': ['Skincare', 'Supplements', 'Personal Care', 'Makeup'],
        'Sports & Outdoors': ['Fitness', 'Outdoor Gear', 'Team Sports', 'Water Sports'],
        'Toys & Games': ['Action Figures', 'Board Games', 'Educational', 'Electronic Toys'],
        'Automotive': ['Parts', 'Accessories', 'Tools', 'Care Products']
    }
    
    products = []
    for i in range(n_products):
        category = random.choice(categories)
        subcategory = random.choice(subcategories[category])
        
        # Generate realistic pricing based on category
        price_ranges = {
            'Electronics': (20, 2000),
            'Clothing': (10, 200),
            'Home & Garden': (15, 500),
            'Food & Beverages': (1, 50),
            'Health & Beauty': (5, 100),
            'Sports & Outdoors': (20, 800),
            'Toys & Games': (5, 150),
            'Automotive': (10, 300)
        }
        
        min_price, max_price = price_ranges[category]
        price = round(np.random.uniform(min_price, max_price), 2)
        
        products.append({
            'product_id': f'PROD{i+1:04d}',
            'product_name': f'{subcategory} Item {i+1}',
            'category': category,
            'subcategory': subcategory,
            'price': price,
            'supplier_lead_time': random.choice([1, 2, 3, 5, 7, 10, 14]),  # days
            'minimum_stock_level': random.randint(5, 100),
            'seasonal_factor': round(np.random.uniform(0.5, 2.0), 2)
        })
    
    return pd.DataFrame(products)

def generate_sales_data(products_df, n_days=365):
    """Generate historical sales data"""
    start_date = datetime.now() - timedelta(days=n_days)
    sales_data = []
    
    for _, product in products_df.iterrows():
        # Base daily demand based on category and price
        category_demand = {
            'Electronics': 50, 'Clothing': 80, 'Home & Garden': 30,
            'Food & Beverages': 200, 'Health & Beauty': 60,
            'Sports & Outdoors': 25, 'Toys & Games': 40, 'Automotive': 15
        }
        
        base_demand = category_demand[product['category']]
        price_factor = max(0.1, 100 / product['price'])  # Higher price = lower demand
        
        for day in range(n_days):
            current_date = start_date + timedelta(days=day)
            
            # Seasonal effects
            month = current_date.month
            seasonal_multiplier = 1.0
            
            # Holiday seasons
            if month in [11, 12]:  # Black Friday/Christmas
                seasonal_multiplier = 1.8
            elif month in [6, 7, 8]:  # Summer
                seasonal_multiplier = 1.2
            elif month in [1, 2]:  # Post-holiday
                seasonal_multiplier = 0.7
            
            # Weekend effects
            if current_date.weekday() >= 5:  # Weekend
                seasonal_multiplier *= 1.3
            
            # Apply seasonal factor from product
            seasonal_multiplier *= product['seasonal_factor']
            
            # Generate demand with noise
            daily_demand = int(np.random.poisson(
                max(1, base_demand * price_factor * seasonal_multiplier * 0.1)
            ))
            
            # Occasional stockout simulation
            stockout_prob = 0.02  # 2% chance of stockout
            if np.random.random() < stockout_prob:
                daily_demand = 0
                stockout = 1
            else:
                stockout = 0
            
            sales_data.append({
                'date': current_date,
                'product_id': product['product_id'],
                'daily_demand': daily_demand,
                'stockout': stockout,
                'day_of_week': current_date.weekday(),
                'month': current_date.month,
                'is_weekend': int(current_date.weekday() >= 5),
                'is_holiday_season': int(month in [11, 12])
            })
    
    return pd.DataFrame(sales_data)

def generate_current_inventory(products_df):
    """Generate current inventory levels"""
    inventory_data = []
    
    for _, product in products_df.iterrows():
        # Current stock level (some products may be low)
        if np.random.random() < 0.1:  # 10% chance of low stock
            current_stock = random.randint(0, product['minimum_stock_level'])
        else:
            current_stock = random.randint(
                product['minimum_stock_level'], 
                product['minimum_stock_level'] * 5
            )
        
        # Days since last restock
        days_since_restock = random.randint(1, 30)
        
        inventory_data.append({
            'product_id': product['product_id'],
            'current_stock': current_stock,
            'minimum_stock_level': product['minimum_stock_level'],
            'days_since_restock': days_since_restock,
            'supplier_lead_time': product['supplier_lead_time'],
            'reorder_point': product['minimum_stock_level'] + 
                           (product['supplier_lead_time'] * 2),  # Simple reorder point
            'last_restock_date': datetime.now() - timedelta(days=days_since_restock)
        })
    
    return pd.DataFrame(inventory_data)

def main():
    """Generate all sample data files"""
    print("Generating sample data for StockSense...")
    
    # Generate product catalog
    print("Creating product catalog...")
    products_df = generate_product_catalog(1000)
    products_df.to_csv('sample_products.csv', index=False)
    
    # Generate historical sales data
    print("Generating historical sales data...")
    sales_df = generate_sales_data(products_df, 365)
    sales_df.to_csv('sample_sales_history.csv', index=False)
    
    # Generate current inventory
    print("Creating current inventory snapshot...")
    inventory_df = generate_current_inventory(products_df)
    inventory_df.to_csv('sample_inventory.csv', index=False)
    
    # Create a summary dataset for ML training
    print("Creating ML training dataset...")
    
    # Aggregate sales data by product
    sales_agg = sales_df.groupby('product_id').agg({
        'daily_demand': ['mean', 'std', 'max'],
        'stockout': 'sum',
        'is_weekend': 'mean',
        'is_holiday_season': 'mean'
    }).reset_index()
    
    # Flatten column names
    sales_agg.columns = [
        'product_id', 'avg_daily_demand', 'demand_std', 'max_daily_demand',
        'total_stockouts', 'weekend_sales_ratio', 'holiday_sales_ratio'
    ]
    
    # Merge with product and inventory data
    ml_dataset = products_df.merge(sales_agg, on='product_id')
    ml_dataset = ml_dataset.merge(inventory_df, on='product_id')
    
    # Calculate risk indicators
    ml_dataset['demand_variability'] = ml_dataset['demand_std'] / ml_dataset['avg_daily_demand']
    ml_dataset['stock_coverage_days'] = ml_dataset['current_stock'] / ml_dataset['avg_daily_demand']
    ml_dataset['is_high_risk'] = (
        (ml_dataset['stock_coverage_days'] <= ml_dataset['supplier_lead_time']) |
        (ml_dataset['current_stock'] <= ml_dataset['minimum_stock_level'])
    ).astype(int)
    
    ml_dataset.to_csv('ml_training_data.csv', index=False)
    
    print("\n✅ Sample data generation completed!")
    print(f"📊 Generated data for {len(products_df)} products")
    print(f"📈 Created {len(sales_df)} sales records")
    print(f"📦 Generated inventory data for {len(inventory_df)} products")
    print(f"🤖 ML training dataset ready with {len(ml_dataset)} samples")
    
    # Print some statistics
    print("\n📋 Data Summary:")
    print(f"  - Products at risk: {ml_dataset['is_high_risk'].sum()}")
    print(f"  - Average daily demand: {ml_dataset['avg_daily_demand'].mean():.2f}")
    print(f"  - Total historical stockouts: {ml_dataset['total_stockouts'].sum()}")

if __name__ == "__main__":
    main()