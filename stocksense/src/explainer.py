"""
StockSense Explainer
Provides explanations and insights for stockout predictions
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import joblib
import logging
from typing import Dict, List, Any
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockSenseExplainer:
    """
    Explainer class for StockSense predictions
    Provides interpretable insights and visualizations
    """
    
    def __init__(self, model_path: str = '../models/stockout_model.pkl'):
        """
        Initialize explainer with trained model
        
        Args:
            model_path (str): Path to trained model file
        """
        self.model_path = model_path
        self.model_data = None
        self.feature_importance = None
        self.load_model()
        
    def load_model(self):
        """Load the trained model and extract feature importance"""
        try:
            self.model_data = joblib.load(self.model_path)
            
            # Extract feature importance if available
            model = self.model_data['model']
            if hasattr(model, 'feature_importances_'):
                feature_names = self.model_data['feature_names']
                importances = model.feature_importances_
                
                self.feature_importance = pd.DataFrame({
                    'feature': feature_names,
                    'importance': importances
                }).sort_values('importance', ascending=False)
                
            logger.info(f"Model and explainer loaded successfully from {self.model_path}")
            
        except FileNotFoundError:
            logger.error(f"Model file not found: {self.model_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def explain_prediction(self, product_data: Dict, prediction_result: Dict) -> Dict:
        """
        Provide detailed explanation for a single product's prediction
        
        Args:
            product_data (dict): Original product data
            prediction_result (dict): Prediction results
            
        Returns:
            dict: Detailed explanation
        """
        explanation = {
            'product_info': {
                'product_id': product_data.get('product_id', 'Unknown'),
                'current_stock': product_data.get('current_stock', 0),
                'daily_demand': product_data.get('avg_daily_demand', 0),
                'lead_time': product_data.get('supplier_lead_time', 7)
            },
            'risk_assessment': {
                'risk_score': prediction_result.get('risk_score', 0),
                'risk_level': prediction_result.get('risk_level', 'Unknown'),
                'risk_category': prediction_result.get('risk_category', 'Unknown')
            },
            'key_factors': self._identify_key_factors(product_data),
            'explanation_narrative': self._generate_narrative(product_data, prediction_result),
            'improvement_suggestions': self._suggest_improvements(product_data, prediction_result)
        }
        
        return explanation
    
    def _identify_key_factors(self, product_data: Dict) -> List[Dict]:
        """
        Identify key factors contributing to the risk assessment
        
        Args:
            product_data (dict): Product information
            
        Returns:
            list: Key risk factors with explanations
        """
        factors = []
        
        current_stock = product_data.get('current_stock', 0)
        daily_demand = product_data.get('avg_daily_demand', 1)
        lead_time = product_data.get('supplier_lead_time', 7)
        min_stock = product_data.get('minimum_stock_level', 10)
        
        # Calculate key metrics
        stock_days = current_stock / max(daily_demand, 1)
        
        # Stock coverage factor
        if stock_days < lead_time:
            factors.append({
                'factor': 'Stock Coverage',
                'value': f"{stock_days:.1f} days",
                'status': 'Critical',
                'impact': 'High',
                'explanation': f"Current stock will last {stock_days:.1f} days, but supplier lead time is {lead_time} days"
            })
        elif stock_days < lead_time * 2:
            factors.append({
                'factor': 'Stock Coverage',
                'value': f"{stock_days:.1f} days", 
                'status': 'Warning',
                'impact': 'Medium',
                'explanation': f"Stock coverage is below recommended safety level (2x lead time)"
            })
        else:
            factors.append({
                'factor': 'Stock Coverage',
                'value': f"{stock_days:.1f} days",
                'status': 'Good',
                'impact': 'Low',
                'explanation': "Stock coverage is adequate"
            })
        
        # Minimum stock level factor
        if current_stock < min_stock:
            factors.append({
                'factor': 'Minimum Stock Level',
                'value': f"{current_stock}/{min_stock}",
                'status': 'Critical',
                'impact': 'High',
                'explanation': f"Current stock ({current_stock}) is below minimum level ({min_stock})"
            })
        
        # Demand variability factor
        demand_std = product_data.get('demand_std', daily_demand * 0.2)
        variability = demand_std / max(daily_demand, 1)
        
        if variability > 0.5:
            factors.append({
                'factor': 'Demand Variability',
                'value': f"{variability:.1%}",
                'status': 'Warning',
                'impact': 'Medium',
                'explanation': "High demand variability increases stockout risk"
            })
        
        # Lead time factor
        if lead_time > 14:
            factors.append({
                'factor': 'Supplier Lead Time',
                'value': f"{lead_time} days",
                'status': 'Warning',
                'impact': 'Medium',
                'explanation': "Long lead time increases planning complexity"
            })
        
        return factors
    
    def _generate_narrative(self, product_data: Dict, prediction_result: Dict) -> str:
        """
        Generate human-readable explanation narrative
        
        Args:
            product_data (dict): Product information
            prediction_result (dict): Prediction results
            
        Returns:
            str: Narrative explanation
        """
        risk_score = prediction_result.get('risk_score', 0)
        current_stock = product_data.get('current_stock', 0)
        daily_demand = product_data.get('avg_daily_demand', 1)
        lead_time = product_data.get('supplier_lead_time', 7)
        
        stock_days = current_stock / max(daily_demand, 1)
        
        if risk_score > 0.7:
            narrative = f"🚨 HIGH RISK: This product has a {risk_score:.0%} chance of stockout. "
            narrative += f"With only {current_stock} units in stock and daily demand of {daily_demand:.1f}, "
            narrative += f"the current inventory will last approximately {stock_days:.1f} days. "
            narrative += f"Given the supplier lead time of {lead_time} days, immediate action is required."
            
        elif risk_score > 0.4:
            narrative = f"⚠️ MEDIUM RISK: This product has a {risk_score:.0%} chance of stockout. "
            narrative += f"Current stock of {current_stock} units provides {stock_days:.1f} days of coverage. "
            narrative += f"Consider reordering soon to maintain adequate inventory levels."
            
        else:
            narrative = f"✅ LOW RISK: This product has a {risk_score:.0%} chance of stockout. "
            narrative += f"Current stock levels appear adequate with {stock_days:.1f} days of coverage. "
            narrative += "Continue monitoring for any changes in demand patterns."
        
        return narrative
    
    def _suggest_improvements(self, product_data: Dict, prediction_result: Dict) -> List[str]:
        """
        Suggest specific improvements to reduce stockout risk
        
        Args:
            product_data (dict): Product information
            prediction_result (dict): Prediction results
            
        Returns:
            list: Improvement suggestions
        """
        suggestions = []
        
        current_stock = product_data.get('current_stock', 0)
        daily_demand = product_data.get('avg_daily_demand', 1)
        lead_time = product_data.get('supplier_lead_time', 7)
        min_stock = product_data.get('minimum_stock_level', 10)
        
        stock_days = current_stock / max(daily_demand, 1)
        safety_stock = daily_demand * lead_time * 1.5
        
        # Immediate actions
        if prediction_result.get('risk_score', 0) > 0.7:
            suggestions.append("📞 Contact supplier immediately for emergency delivery")
            suggestions.append("🔍 Review alternative suppliers for faster delivery")
            suggestions.append("📊 Implement daily stock monitoring for this product")
        
        # Inventory management improvements
        if current_stock < safety_stock:
            reorder_qty = int(safety_stock - current_stock + daily_demand * 7)  # Add 1 week buffer
            suggestions.append(f"📦 Increase order quantity to {reorder_qty} units")
        
        if stock_days < lead_time * 2:
            new_reorder_point = int(daily_demand * lead_time * 2)
            suggestions.append(f"🎯 Set reorder point to {new_reorder_point} units (2x lead time demand)")
        
        # Process improvements
        if lead_time > 10:
            suggestions.append("🤝 Negotiate shorter lead times with supplier")
            suggestions.append("🏪 Consider local suppliers to reduce lead time")
        
        demand_std = product_data.get('demand_std', daily_demand * 0.2)
        if demand_std / daily_demand > 0.4:
            suggestions.append("📈 Implement demand forecasting to better predict variations")
            suggestions.append("📊 Analyze demand patterns to identify trends")
        
        # Technology improvements
        suggestions.append("🤖 Set up automated reorder alerts")
        suggestions.append("📱 Implement real-time inventory tracking")
        
        return suggestions
    
    def create_feature_importance_plot(self, top_n: int = 15) -> go.Figure:
        """
        Create interactive feature importance plot
        
        Args:
            top_n (int): Number of top features to display
            
        Returns:
            plotly Figure: Interactive feature importance plot
        """
        if self.feature_importance is None:
            logger.warning("Feature importance not available")
            return go.Figure()
        
        top_features = self.feature_importance.head(top_n)
        
        fig = px.bar(
            top_features,
            x='importance',
            y='feature',
            orientation='h',
            title=f'Top {top_n} Feature Importances',
            labels={'importance': 'Importance Score', 'feature': 'Feature'},
            color='importance',
            color_continuous_scale='Reds'
        )
        
        fig.update_layout(
            height=600,
            yaxis={'categoryorder': 'total ascending'},
            showlegend=False
        )
        
        return fig
    
    def create_risk_distribution_plot(self, predictions_df: pd.DataFrame) -> go.Figure:
        """
        Create risk distribution visualization
        
        Args:
            predictions_df (DataFrame): Prediction results
            
        Returns:
            plotly Figure: Risk distribution plot
        """
        if 'risk_score' not in predictions_df.columns:
            logger.warning("Risk scores not found in predictions")
            return go.Figure()
        
        fig = px.histogram(
            predictions_df,
            x='risk_score',
            nbins=20,
            title='Risk Score Distribution',
            labels={'risk_score': 'Risk Score', 'count': 'Number of Products'},
            color_discrete_sequence=['skyblue']
        )
        
        # Add risk threshold lines
        fig.add_vline(x=0.3, line_dash="dash", line_color="green", 
                      annotation_text="Low Risk Threshold")
        fig.add_vline(x=0.7, line_dash="dash", line_color="red", 
                      annotation_text="High Risk Threshold")
        
        fig.update_layout(height=400)
        
        return fig
    
    def create_risk_factors_radar(self, product_data: Dict) -> go.Figure:
        """
        Create radar chart showing risk factors for a single product
        
        Args:
            product_data (dict): Product information
            
        Returns:
            plotly Figure: Radar chart
        """
        # Calculate normalized risk factors (0-1 scale)
        current_stock = product_data.get('current_stock', 0)
        daily_demand = max(product_data.get('avg_daily_demand', 1), 1)
        lead_time = product_data.get('supplier_lead_time', 7)
        min_stock = product_data.get('minimum_stock_level', 10)
        
        # Normalize factors (higher = more risk)
        factors = {
            'Stock Coverage Risk': max(0, min(1, 1 - (current_stock / daily_demand) / (lead_time * 2))),
            'Lead Time Risk': min(1, lead_time / 21),  # 21 days = max risk
            'Minimum Stock Risk': max(0, min(1, 1 - current_stock / min_stock)) if min_stock > 0 else 0,
            'Demand Variability': min(1, product_data.get('demand_std', daily_demand * 0.2) / daily_demand),
            'Historical Stockouts': min(1, product_data.get('total_stockouts', 0) / 10),  # 10+ = max risk
        }
        
        categories = list(factors.keys())
        values = list(factors.values())
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Risk Factors',
            line_color='red',
            fillcolor='rgba(255,0,0,0.1)'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )),
            showlegend=False,
            title="Risk Factors Analysis"
        )
        
        return fig
    
    def generate_executive_summary(self, predictions_df: pd.DataFrame) -> Dict:
        """
        Generate executive summary of inventory risk
        
        Args:
            predictions_df (DataFrame): Prediction results
            
        Returns:
            dict: Executive summary data
        """
        total_products = len(predictions_df)
        
        if 'risk_score' not in predictions_df.columns:
            return {'error': 'Risk scores not available'}
        
        high_risk = (predictions_df['risk_score'] >= 0.7).sum()
        medium_risk = ((predictions_df['risk_score'] >= 0.3) & 
                      (predictions_df['risk_score'] < 0.7)).sum()
        low_risk = (predictions_df['risk_score'] < 0.3).sum()
        
        avg_risk = predictions_df['risk_score'].mean()
        
        # Calculate potential impact
        if 'current_stock' in predictions_df.columns and 'price' in predictions_df.columns:
            high_risk_products = predictions_df[predictions_df['risk_score'] >= 0.7]
            potential_lost_sales = (high_risk_products['current_stock'] * 
                                  high_risk_products.get('price', 50)).sum()
        else:
            potential_lost_sales = None
        
        # Top risk categories
        category_risk = None
        if 'category' in predictions_df.columns:
            category_risk = predictions_df.groupby('category')['risk_score'].mean().sort_values(ascending=False)
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'overview': {
                'total_products': total_products,
                'high_risk_count': int(high_risk),
                'medium_risk_count': int(medium_risk),
                'low_risk_count': int(low_risk),
                'average_risk_score': round(float(avg_risk), 3),
                'risk_percentage': round(float(high_risk) / total_products * 100, 1)
            },
            'insights': [
                f"{high_risk} products ({high_risk/total_products:.1%}) are at high risk of stockout",
                f"Average risk score across all products is {avg_risk:.1%}",
                f"Immediate attention required for {high_risk} high-risk products"
            ],
            'recommendations': [
                "Focus on high-risk products for immediate reordering",
                "Review supplier agreements for products with long lead times",
                "Implement automated monitoring for medium-risk products",
                "Consider increasing safety stock levels for volatile products"
            ]
        }
        
        if potential_lost_sales:
            summary['financial_impact'] = {
                'potential_lost_sales': round(float(potential_lost_sales), 2),
                'currency': 'USD'
            }
            summary['insights'].append(
                f"Potential lost sales from high-risk products: ${potential_lost_sales:,.2f}"
            )
        
        if category_risk is not None:
            summary['category_analysis'] = category_risk.head(5).to_dict()
        
        return summary

def main():
    """
    Main function for testing the explainer
    """
    try:
        explainer = StockSenseExplainer()
        
        # Test sample explanation
        sample_product = {
            'product_id': 'TEST001',
            'current_stock': 15,
            'avg_daily_demand': 5,
            'supplier_lead_time': 7,
            'minimum_stock_level': 20,
            'price': 25.99,
            'category': 'Electronics',
            'demand_std': 1.5,
            'total_stockouts': 2
        }
        
        sample_prediction = {
            'risk_score': 0.75,
            'risk_level': 'High',
            'risk_category': 'High Risk'
        }
        
        explanation = explainer.explain_prediction(sample_product, sample_prediction)
        
        print("🔍 StockSense Explanation Test:")
        print("=" * 50)
        print(f"\nProduct: {explanation['product_info']['product_id']}")
        print(f"Risk Level: {explanation['risk_assessment']['risk_level']}")
        print(f"Risk Score: {explanation['risk_assessment']['risk_score']:.1%}")
        
        print(f"\n📖 Explanation:")
        print(explanation['explanation_narrative'])
        
        print(f"\n🔧 Key Factors:")
        for factor in explanation['key_factors']:
            print(f"  • {factor['factor']}: {factor['value']} ({factor['status']})")
        
        print(f"\n💡 Suggestions:")
        for suggestion in explanation['improvement_suggestions'][:3]:
            print(f"  • {suggestion}")
        
        logger.info("✅ Explainer testing completed successfully!")
        
    except Exception as e:
        logger.error(f"Error testing explainer: {e}")

if __name__ == "__main__":
    main()