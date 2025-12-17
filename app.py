"""
Azure 0rphans
Azure App Service Plans cost optimization analyzer
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import pandas as pd
import numpy as np
import re
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from azure.identity import AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.frontdoor import FrontDoorManagementClient
import subprocess
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DATA_FOLDER'] = 'data/app-services'
app.config['ENVIRONMENT_FOLDER'] = 'data/environment'

# Demo mode - controlled via UI toggle stored in session
# Demo mode:
#   - Scan files are saved with 'azure_scan_demo_' prefix
#   - Only demo files are shown in the UI
#   - Delete operations are blocked for demo files
DEV_FILE_PREFIX = 'azure_scan_demo_'
PROD_FILE_PREFIX = 'azure_scan_production_'

# Helper function to check demo mode from session
def is_demo_mode():
    return session.get('demo_mode', False)

# Ensure data directories exist
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)
os.makedirs(app.config['ENVIRONMENT_FOLDER'], exist_ok=True)

# Resource type configurations
RESOURCE_TYPES = {
    'app-service': {
        'name': 'App Service Plans',
        'icon': 'bi-diagram-3',
        'description': 'Analyze App Service Plans and App Services for cost optimization',
        'color': 'primary',
        'gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'enabled': True
    },
    'sql-databases': {
        'name': 'SQL Databases & Elastic Pools',
        'icon': 'bi-database',
        'description': 'Optimize SQL databases, elastic pools, and DTU allocations',
        'color': 'success',
        'gradient': 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
        'enabled': True
    },
    'virtual-machines': {
        'name': 'Virtual Machines',
        'icon': 'bi-cpu',
        'description': 'Right-size VMs, identify stopped instances, and optimize SKUs',
        'color': 'danger',
        'gradient': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'enabled': True
    },
    'public-ips': {
        'name': 'Public IP Addresses',
        'icon': 'bi-globe',
        'description': 'Find unattached public IPs and optimize IP allocations',
        'color': 'info',
        'gradient': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        'enabled': True
    },
    'disks': {
        'name': 'Managed Disks',
        'icon': 'bi-device-hdd',
        'description': 'Identify unattached disks and optimize disk tiers',
        'color': 'warning',
        'gradient': 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
        'enabled': True
    },
    'nics': {
        'name': 'Network Interfaces',
        'icon': 'bi-ethernet',
        'description': 'Find orphaned NICs and optimize network configurations',
        'color': 'secondary',
        'gradient': 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
        'enabled': True
    },
    'load-balancers': {
        'name': 'Load Balancers',
        'icon': 'bi-arrows-angle-expand',
        'description': 'Optimize load balancers and backend pool configurations',
        'color': 'primary',
        'gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'enabled': True
    },
    'availability-sets': {
        'name': 'Availability Sets',
        'icon': 'bi-building',
        'description': 'Find empty availability sets and consolidate resources',
        'color': 'info',
        'gradient': 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
        'enabled': True
    },
    'route-tables': {
        'name': 'Route Tables',
        'icon': 'bi-signpost-2',
        'description': 'Optimize route tables and identify unused routes',
        'color': 'success',
        'gradient': 'linear-gradient(135deg, #29ffc6 0%, #20e3b2 100%)',
        'enabled': True
    },
    'nat-gateways': {
        'name': 'NAT Gateways',
        'icon': 'bi-arrow-left-right',
        'description': 'Review NAT gateway usage and costs',
        'color': 'warning',
        'gradient': 'linear-gradient(135deg, #FFD700 0%, #FFA500 100%)',
        'enabled': True
    },
    'frontdoor-waf': {
        'name': 'Front Door WAF Policies',
        'icon': 'bi-shield-check',
        'description': 'Optimize WAF policies and Front Door configurations',
        'color': 'danger',
        'gradient': 'linear-gradient(135deg, #ff0844 0%, #ffb199 100%)',
        'enabled': True
    },
    'traffic-manager': {
        'name': 'Traffic Manager Profiles',
        'icon': 'bi-diagram-3',
        'description': 'Analyze Traffic Manager profiles and endpoint health',
        'color': 'primary',
        'gradient': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        'enabled': True
    },
    'subnets': {
        'name': 'Virtual Network Subnets',
        'icon': 'bi-diagram-2',
        'description': 'Optimize subnet IP allocations and identify unused subnets',
        'color': 'info',
        'gradient': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        'enabled': True
    },
    'ip-groups': {
        'name': 'IP Groups',
        'icon': 'bi-collection',
        'description': 'Review IP group configurations and usage',
        'color': 'secondary',
        'gradient': 'linear-gradient(135deg, #d299c2 0%, #fef9d7 100%)',
        'enabled': True
    },
    'private-dns': {
        'name': 'Private DNS Zones',
        'icon': 'bi-server',
        'description': 'Optimize private DNS zones and record sets',
        'color': 'success',
        'gradient': 'linear-gradient(135deg, #0ba360 0%, #3cba92 100%)',
        'enabled': True
    },
    'private-endpoints': {
        'name': 'Private Endpoints',
        'icon': 'bi-plugin',
        'description': 'Review private endpoint connections and costs',
        'color': 'warning',
        'gradient': 'linear-gradient(135deg, #f8b500 0%, #fceabb 100%)',
        'enabled': True
    },
    'vnet-gateways': {
        'name': 'Virtual Network Gateways',
        'icon': 'bi-door-closed',
        'description': 'Optimize VPN and ExpressRoute gateway configurations',
        'color': 'danger',
        'gradient': 'linear-gradient(135deg, #eb3349 0%, #f45c43 100%)',
        'enabled': True
    },
    'ddos-plans': {
        'name': 'DDoS Protection Plans',
        'icon': 'bi-shield-fill-check',
        'description': 'Review DDoS protection coverage and costs',
        'color': 'primary',
        'gradient': 'linear-gradient(135deg, #5f72bd 0%, #9b23ea 100%)',
        'enabled': True
    },
    'api-connections': {
        'name': 'API Connections',
        'icon': 'bi-link-45deg',
        'description': 'Optimize Logic Apps API connections',
        'color': 'info',
        'gradient': 'linear-gradient(135deg, #6a11cb 0%, #2575fc 100%)',
        'enabled': True
    },
    'certificates': {
        'name': 'App Service Certificates',
        'icon': 'bi-file-earmark-lock',
        'description': 'Manage SSL/TLS certificates and expiration dates',
        'color': 'success',
        'gradient': 'linear-gradient(135deg, #56ab2f 0%, #a8e063 100%)',
        'enabled': True
    },
    'storage-accounts': {
        'name': 'Storage Accounts',
        'icon': 'bi-archive',
        'description': 'Optimize storage tiers and identify unused accounts',
        'color': 'warning',
        'gradient': 'linear-gradient(135deg, #f2994a 0%, #f2c94c 100%)',
        'enabled': True
    },
    'nsgs': {
        'name': 'Network Security Groups',
        'icon': 'bi-shield-lock',
        'description': 'Review NSG rules and security configurations',
        'color': 'danger',
        'gradient': 'linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%)',
        'enabled': True
    }
}

def convert_to_serializable(obj):
    """Convert numpy/pandas types to Python native types for JSON serialization"""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj


# ============================================================================
# APP SERVICE PLANS ANALYZER
# ============================================================================

APP_SERVICE_RECOMMENDATIONS = {
    'oversized_plans': {
        'title': 'Oversized App Service Plans',
        'description': 'Plans with high instance counts but few apps may be oversized',
        'impact': 'High',
        'category': 'Right-sizing'
    },
    'premium_underutilized': {
        'title': 'Underutilized Premium Plans',
        'description': 'Premium V3 plans with only 1-2 apps could be consolidated',
        'impact': 'Medium',
        'category': 'Consolidation'
    },
    'basic_consolidation': {
        'title': 'Basic Tier Consolidation',
        'description': 'Multiple Basic tier plans can be consolidated into fewer plans',
        'impact': 'Medium',
        'category': 'Consolidation'
    },
    'mixed_locations': {
        'title': 'Cross-Region Deployments',
        'description': 'Apps spread across multiple regions may incur data transfer costs',
        'impact': 'Low',
        'category': 'Architecture'
    },
    'standard_upgrade': {
        'title': 'Consider Premium V3 for Better ROI',
        'description': 'Standard plans could benefit from Premium V3 reserved instances',
        'impact': 'Medium',
        'category': 'Optimization'
    },
    'stopped_apps': {
        'title': 'Stopped Apps Still Consuming Resources',
        'description': 'Apps that are stopped but still deployed on a plan',
        'impact': 'Medium',
        'category': 'Cost Waste'
    },
    'high_app_density': {
        'title': 'High App Density on Single Plan',
        'description': 'Many apps on one plan may impact performance and isolation',
        'impact': 'Low',
        'category': 'Performance'
    },
    'orphaned_apps': {
        'title': 'Apps Reference Missing Plans',
        'description': 'Apps data references plans not in the plans export',
        'impact': 'Low',
        'category': 'Data Quality'
    },
    'region_mismatch': {
        'title': 'Plan and App Region Mismatch',
        'description': 'Apps appear to be in different region than their plan',
        'impact': 'Low',
        'category': 'Data Quality'
    },
    'limited_analysis': {
        'title': 'Limited Analysis - Missing Plans Data',
        'description': 'Analysis is based on Apps data only',
        'impact': 'N/A',
        'category': 'Information'
    }
}

def parse_pricing_tier(tier_string):
    """Extract tier name and instance count from pricing tier string"""
    match = re.search(r'(.*?)\s*\((.*?):\s*(\d+)\)', tier_string)
    if match:
        tier_name = match.group(1).strip()
        sku = match.group(2).strip()
        instances = int(match.group(3))
        return tier_name, sku, instances
    return tier_string, 'Unknown', 1

def convert_json_to_app_service_dataframe(plans_data):
    """Convert JSON App Service Plans data to DataFrame format for analysis"""
    records = []
    for plan in plans_data:
        # Construct pricing tier string (e.g., "P1v3: Premium V3 Small 1")
        sku_name = plan.get('sku_name', 'Unknown')
        tier = plan.get('sku_tier', 'Unknown')
        size = plan.get('sku_size', '')
        capacity = plan.get('sku_capacity', 1)
        pricing_tier = f"{sku_name}: {tier} {size} {capacity}"
        
        # Determine OS from kind (linux, app, functionapp, etc.)
        kind = plan.get('kind', 'app')
        os = 'Linux' if 'linux' in kind.lower() else 'Windows'
        
        records.append({
            'NAME': plan.get('name'),
            'RESOURCE GROUP': plan.get('resource_group'),
            'LOCATION': plan.get('location'),
            'PRICING TIER': pricing_tier,
            'OPERATING SYSTEM': os,
            'APPS': plan.get('num_apps', 0),
            'STATUS': 'Running',
            'SKU': sku_name,
            'TIER': tier
        })
    
    return pd.DataFrame(records)

def analyze_app_service_plans(csv_path):
    """Load and analyze App Service Plans data"""
    df = pd.read_csv(csv_path)
    
    df[['TIER_NAME', 'SKU', 'INSTANCES']] = df['PRICING TIER'].apply(
        lambda x: pd.Series(parse_pricing_tier(x))
    )
    
    total_instances = df['INSTANCES'].sum()
    total_apps = df['APPS'].sum()
    total_plans = len(df)
    
    # Group by SKU and OS for detailed breakdown
    tier_stats = df.groupby(['SKU', 'OPERATING SYSTEM']).agg({
        'NAME': 'count',
        'APPS': 'sum',
        'INSTANCES': 'sum'
    }).reset_index()
    tier_stats.columns = ['Tier', 'OS', 'Plans', 'Apps', 'Instances']
    tier_stats = tier_stats.sort_values(['Tier', 'OS'], ascending=[False, True])
    
    location_stats = df.groupby('LOCATION').agg({
        'NAME': 'count',
        'APPS': 'sum',
        'INSTANCES': 'sum'
    }).reset_index()
    location_stats.columns = ['Location', 'Plans', 'Apps', 'Instances']
    
    os_stats = df.groupby('OPERATING SYSTEM').agg({
        'NAME': 'count',
        'APPS': 'sum'
    }).reset_index()
    os_stats.columns = ['OS', 'Plans', 'Apps']
    
    rg_stats = df.groupby('RESOURCE GROUP').agg({
        'NAME': 'count',
        'APPS': 'sum',
        'INSTANCES': 'sum'
    }).reset_index()
    rg_stats.columns = ['ResourceGroup', 'Plans', 'Apps', 'Instances']
    rg_stats = rg_stats.sort_values('Plans', ascending=False)
    
    return {
        'df': df,
        'summary': {
            'total_plans': total_plans,
            'total_apps': total_apps,
            'total_instances': total_instances,
            'avg_apps_per_plan': round(total_apps / total_plans, 2)
        },
        'tier_stats': tier_stats.to_dict('records'),
        'location_stats': location_stats.to_dict('records'),
        'os_stats': os_stats.to_dict('records'),
        'rg_stats': rg_stats.to_dict('records')
    }

def analyze_app_services_only(csv_path):
    """Analyze App Services CSV when Plans CSV is not available"""
    df = pd.read_csv(csv_path)
    
    total_apps = len(df)
    unique_plans = df['APP SERVICE PLAN'].nunique() if 'APP SERVICE PLAN' in df.columns else 0
    
    # Get status breakdown
    running = stopped = 0
    if 'STATUS' in df.columns:
        running = len(df[df['STATUS'].str.contains('Running', case=False, na=False)])
        stopped = len(df[~df['STATUS'].str.contains('Running', case=False, na=False)])
    
    # Group by plan - extract just the plan name from the full resource path
    plan_stats = None
    if 'APP SERVICE PLAN' in df.columns:
        # Extract plan name from path like /subscriptions/.../serverfarms/PlanName
        df['PLAN_NAME'] = df['APP SERVICE PLAN'].apply(
            lambda x: x.split('/')[-1] if isinstance(x, str) and '/' in x else x
        )
        plan_stats = df.groupby('PLAN_NAME').size().reset_index()
        plan_stats.columns = ['Plan', 'Apps']
        plan_stats = plan_stats.sort_values('Apps', ascending=False)
    
    # Group by location
    location_stats = None
    if 'LOCATION' in df.columns:
        location_stats = df.groupby('LOCATION').size().reset_index()
        location_stats.columns = ['Location', 'Apps']
    
    # Group by pricing tier
    tier_stats = None
    if 'PRICING TIER' in df.columns:
        tier_stats = df.groupby('PRICING TIER').size().reset_index()
        tier_stats.columns = ['Tier', 'Apps']
    
    # Group by subscription (resource groups not typically in app services export)
    subscription_stats = None
    if 'SUBSCRIPTION' in df.columns:
        subscription_stats = df.groupby('SUBSCRIPTION').size().reset_index()
        subscription_stats.columns = ['Subscription', 'Apps']
        subscription_stats = subscription_stats.sort_values('Apps', ascending=False)
    
    # Note: OS information (Windows/Linux) is only available in App Service Plans CSV
    # The Apps CSV doesn't contain this information
    os_stats = None
    
    return {
        'df': df,
        'summary': {
            'total_plans': unique_plans,
            'total_apps': total_apps,
            'total_instances': 0,  # Not available without plans data
            'avg_apps_per_plan': round(total_apps / unique_plans, 2) if unique_plans > 0 else 0
        },
        'running_apps': running,
        'stopped_apps': stopped,
        'plan_stats': plan_stats.to_dict('records') if plan_stats is not None else [],
        'location_stats': location_stats.to_dict('records') if location_stats is not None else [],
        'tier_stats': tier_stats.to_dict('records') if tier_stats is not None else [],
        'subscription_stats': subscription_stats.to_dict('records') if subscription_stats is not None else [],
        'os_stats': os_stats.to_dict('records') if os_stats is not None else []
    }

def generate_app_service_recommendations(df):
    """Generate App Service cost optimization recommendations"""
    recommendations = []
    
    oversized = df[(df['INSTANCES'] >= 5) & (df['APPS'] <= 2)]
    if not oversized.empty:
        for _, row in oversized.iterrows():
            recommendations.append({
                'type': 'oversized_plans',
                'resource': row['NAME'],
                'current_state': f"{row['INSTANCES']} instances, {row['APPS']} app(s)",
                'suggestion': f"Consider reducing instances or consolidating apps",
                'potential_saving': 'High',
                'tier': row['TIER_NAME']
            })
    
    premium_underutilized = df[
        (df['TIER_NAME'].str.contains('Premium V3', na=False)) & 
        (df['APPS'] <= 2) &
        (df['INSTANCES'] <= 2)
    ]
    if not premium_underutilized.empty:
        for _, row in premium_underutilized.iterrows():
            recommendations.append({
                'type': 'premium_underutilized',
                'resource': row['NAME'],
                'current_state': f"Premium V3 with {row['APPS']} app(s)",
                'suggestion': "Consolidate multiple Premium plans or consider Standard tier",
                'potential_saving': 'Medium',
                'tier': row['TIER_NAME']
            })
    
    basic_plans = df[df['TIER_NAME'].str.contains('Basic', na=False)]
    if len(basic_plans) > 3:
        recommendations.append({
            'type': 'basic_consolidation',
            'resource': f"{len(basic_plans)} Basic tier plans",
            'current_state': f"{len(basic_plans)} separate Basic plans",
            'suggestion': "Consolidate Basic tier apps into fewer plans",
            'potential_saving': 'Medium',
            'tier': 'Basic'
        })
    
    locations = df['LOCATION'].unique()
    if len(locations) > 1:
        location_counts = df['LOCATION'].value_counts().to_dict()
        recommendations.append({
            'type': 'mixed_locations',
            'resource': f"{len(locations)} different regions",
            'current_state': ', '.join([f"{loc}: {count}" for loc, count in list(location_counts.items())[:3]]),
            'suggestion': "Review data transfer costs between regions and consolidate where possible",
            'potential_saving': 'Low-Medium',
            'tier': 'All'
        })
    
    standard_plans = df[df['TIER_NAME'].str.contains('Standard', na=False)]
    if not standard_plans.empty:
        recommendations.append({
            'type': 'standard_upgrade',
            'resource': f"{len(standard_plans)} Standard plan(s)",
            'current_state': "Using Standard tier",
            'suggestion': "Consider Premium V3 reserved instances for better cost efficiency",
            'potential_saving': 'Up to 55% with 1-3 year reservation',
            'tier': 'Standard'
        })
    
    single_app_plans = df[df['APPS'] == 1]
    if len(single_app_plans) > 5:
        premium_single = single_app_plans[single_app_plans['TIER_NAME'].str.contains('Premium', na=False)]
        if not premium_single.empty:
            recommendations.append({
                'type': 'premium_underutilized',
                'resource': f"{len(premium_single)} Premium plans with single apps",
                'current_state': "One app per plan",
                'suggestion': "Consolidate compatible apps into shared Premium plans",
                'potential_saving': 'High',
                'tier': 'Premium V3'
            })
    
    return recommendations

def calculate_app_service_density(df):
    """Calculate app density metrics"""
    density_data = []
    
    for _, row in df.iterrows():
        apps_per_instance = row['APPS'] / row['INSTANCES'] if row['INSTANCES'] > 0 else 0
        
        if apps_per_instance < 1:
            status = 'Underutilized'
            color = 'danger'
        elif apps_per_instance < 2:
            status = 'Low Density'
            color = 'warning'
        elif apps_per_instance < 4:
            status = 'Good'
            color = 'info'
        else:
            status = 'Optimal'
            color = 'success'
        
        density_data.append({
            'plan_name': row['NAME'],
            'apps': row['APPS'],
            'instances': row['INSTANCES'],
            'density': round(apps_per_instance, 2),
            'tier': row['TIER_NAME'],
            'status': status,
            'color': color,
            'location': row['LOCATION']
        })
    
    return sorted(density_data, key=lambda x: x['density'])

def generate_apps_only_recommendations(apps_df):
    """Generate recommendations based on Apps CSV only"""
    recommendations = []
    
    # Check for stopped apps
    if 'STATUS' in apps_df.columns:
        stopped = apps_df[~apps_df['STATUS'].str.contains('Running', case=False, na=False)]
        if len(stopped) > 0:
            for _, app in stopped.iterrows():
                recommendations.append({
                    'type': 'stopped_apps',
                    'resource': app['NAME'],
                    'current_state': f"Status: {app.get('STATUS', 'Unknown')}",
                    'suggestion': 'Consider removing stopped apps to clean up resources',
                    'potential_saving': 'Low',
                    'tier': app.get('PRICING TIER', 'Unknown')
                })
    
    # Check for high concentration on single plan
    if 'APP SERVICE PLAN' in apps_df.columns:
        plan_counts = apps_df['APP SERVICE PLAN'].value_counts()
        high_density = plan_counts[plan_counts > 10]
        
        for plan_name, count in high_density.items():
            recommendations.append({
                'type': 'high_app_density',
                'resource': plan_name,
                'current_state': f"{count} apps on this plan",
                'suggestion': 'Consider splitting apps across multiple plans for better isolation',
                'potential_saving': 'Low (Improved performance)',
                'tier': 'All'
            })
    
    # Note about missing plans data
    if len(recommendations) < 3:
        recommendations.append({
            'type': 'limited_analysis',
            'resource': 'Analysis Scope',
            'current_state': 'Analyzing apps data only',
            'suggestion': 'Upload App Service Plans CSV (file 1) for complete cost optimization analysis',
            'potential_saving': 'N/A',
            'tier': 'All'
        })
    
    return recommendations


# ============================================================================
# COMBINED APP SERVICES ANALYZER (Plans + Apps)
# ============================================================================

def analyze_combined_app_services(plans_csv_path, apps_csv_path):
    """Analyze App Service Plans + App Services together for deeper insights"""
    
    # Load both datasets
    plans_df = pd.read_csv(plans_csv_path)
    apps_df = pd.read_csv(apps_csv_path)
    
    # Parse plan tier information
    plans_df[['TIER_NAME', 'SKU', 'INSTANCES']] = plans_df['PRICING TIER'].apply(
        lambda x: pd.Series(parse_pricing_tier(x))
    )
    
    # Basic stats
    total_plans = len(plans_df)
    total_apps = len(apps_df)
    
    # Try to match apps to plans (if possible via plan name or resource group)
    # This depends on the actual CSV structure from Azure
    
    return {
        'summary': {
            'total_plans': total_plans,
            'total_apps': total_apps,
            'total_instances': int(plans_df['INSTANCES'].sum()),
            'apps_per_plan': round(total_apps / total_plans, 2) if total_plans > 0 else 0
        },
        'combined_insights': True
    }

def generate_combined_recommendations(plans_df, apps_df):
    """Generate recommendations using both plans and apps data"""
    recommendations = []
    
    # Make sure we have the APP SERVICE PLAN column in apps
    if 'APP SERVICE PLAN' not in apps_df.columns:
        return recommendations
    
    # Analyze app distribution across plans
    apps_per_plan = apps_df.groupby('APP SERVICE PLAN').size()
    
    # Find plans with apps that aren't running
    if 'STATUS' in apps_df.columns:
        stopped_apps = apps_df[apps_df['STATUS'].str.contains('Stop|Disabled', case=False, na=False)]
        if len(stopped_apps) > 0:
            for plan_name in stopped_apps['APP SERVICE PLAN'].unique():
                stopped_count = len(stopped_apps[stopped_apps['APP SERVICE PLAN'] == plan_name])
                total_in_plan = len(apps_df[apps_df['APP SERVICE PLAN'] == plan_name])
                
                recommendations.append({
                    'type': 'stopped_apps',
                    'resource': f'{plan_name} ({stopped_count} stopped apps)',
                    'current_state': f'{stopped_count} of {total_in_plan} apps are stopped',
                    'suggestion': 'Review stopped apps - consider removing if no longer needed to save on plan costs',
                    'potential_saving': 'Medium',
                    'tier': 'All'
                })
    
    # Find plans mentioned in apps but with high app counts
    plan_app_counts = apps_df['APP SERVICE PLAN'].value_counts()
    high_density_plans = plan_app_counts[plan_app_counts > 10]
    
    if len(high_density_plans) > 0:
        for plan_name, app_count in high_density_plans.items():
            recommendations.append({
                'type': 'high_app_density',
                'resource': f'{plan_name}',
                'current_state': f'{app_count} apps on single plan',
                'suggestion': 'Consider splitting high-density plans across multiple plans for better isolation and scaling',
                'potential_saving': 'Low (Better performance/reliability)',
                'tier': 'All'
            })
    
    # Find orphaned apps (apps without corresponding plan in plans_df)
    plan_names_in_plans = set(plans_df['NAME'].unique())
    plan_names_in_apps = set(apps_df['APP SERVICE PLAN'].unique())
    orphaned = plan_names_in_apps - plan_names_in_plans
    
    if orphaned:
        recommendations.append({
            'type': 'orphaned_apps',
            'resource': f'{len(orphaned)} plan(s) with apps but not in plans export',
            'current_state': f'Apps reference plans: {", ".join(list(orphaned)[:3])}{"..." if len(orphaned) > 3 else ""}',
            'suggestion': 'Re-export plans data to get complete view, or these apps may be on deleted plans',
            'potential_saving': 'N/A',
            'tier': 'All'
        })
    
    # Cross-region deployment check
    if 'LOCATION' in apps_df.columns:
        app_locations = set(apps_df['LOCATION'].unique())
        plan_locations = set(plans_df['LOCATION'].unique())
        
        # Group by plan and check if apps are in different regions
        for plan_name in plans_df['NAME'].unique():
            plan_location = plans_df[plans_df['NAME'] == plan_name]['LOCATION'].iloc[0]
            plan_apps = apps_df[apps_df['APP SERVICE PLAN'] == plan_name]
            
            if len(plan_apps) > 0:
                app_regions = plan_apps['LOCATION'].unique()
                if len(app_regions) > 1 or (len(app_regions) == 1 and app_regions[0] != plan_location):
                    recommendations.append({
                        'type': 'region_mismatch',
                        'resource': f'{plan_name}',
                        'current_state': f'Plan in {plan_location}, apps in {", ".join(app_regions)}',
                        'suggestion': 'Apps should be in same region as their plan - this may indicate data export issue',
                        'potential_saving': 'N/A',
                        'tier': 'All'
                    })
    
    return recommendations


# ============================================================================
# AZURE ORPHANED RESOURCES DETECTION
# ============================================================================

def get_azure_credential():
    """Get Azure CLI credential"""
    try:
        credential = AzureCliCredential()
        return credential
    except Exception as e:
        print(f"Error getting Azure credentials: {e}")
        return None

def get_subscription_id():
    """Get current Azure subscription ID from Azure CLI"""
    try:
        result = subprocess.run(['az', 'account', 'show', '--query', 'id', '-o', 'tsv'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error getting subscription ID: {e}")
        return None

def download_azure_environment():
    """Download all Azure environment information with detailed properties for orphan detection"""
    try:
        credential = get_azure_credential()
        subscription_id = get_subscription_id()
        
        if not credential or not subscription_id:
            return {'error': 'Unable to authenticate with Azure CLI'}
        
        # Initialize clients
        resource_client = ResourceManagementClient(credential, subscription_id)
        network_client = NetworkManagementClient(credential, subscription_id)
        compute_client = ComputeManagementClient(credential, subscription_id)
        web_client = WebSiteManagementClient(credential, subscription_id)
        sql_client = SqlManagementClient(credential, subscription_id)
        frontdoor_client = FrontDoorManagementClient(credential, subscription_id)
        
        environment_data = {
            'subscription_id': subscription_id,
            'timestamp': datetime.now().isoformat(),
            'resources': {
                'disks': [],
                'public_ips': [],
                'network_interfaces': [],
                'network_security_groups': [],
                'route_tables': [],
                'load_balancers': [],
                'frontdoor_waf_policies': [],
                'traffic_manager_profiles': [],
                'application_gateways': [],
                'virtual_networks': [],
                'subnets': [],
                'ip_groups': [],
                'private_dns_zones': [],
                'private_endpoints': [],
                'virtual_network_gateways': [],
                'ddos_protection_plans': [],
                'api_connections': [],
                'certificates': [],
                'availability_sets': [],
                'nat_gateways': [],
                'app_service_plans': [],
                'sql_servers': [],
                'resource_groups': []
            }
        }
        
        print("Fetching Azure resources with detailed properties...")
        
        # Disks - Unattached state and not related to ASR
        print("  - Fetching disks...")
        for disk in compute_client.disks.list():
            disk_name = disk.name.lower()
            tags_str = str(disk.tags).lower() if disk.tags else ""
            
            # Exclude ASR disks (naming patterns)
            is_asr = disk_name.endswith("-asrreplica") or disk_name.startswith("ms-asr-") or disk_name.startswith("asrseeddisk-")
            
            # Exclude AKS PVC and backup disks (tags)
            is_excluded = ("kubernetes.io-created-for-pvc" in tags_str or 
                          "asr-replicadisk" in tags_str or 
                          "asrseeddisk" in tags_str or 
                          "rsvaultbackup" in tags_str)
            
            # Orphaned criteria: (managedBy empty AND not ActiveSAS) OR (Unattached AND not ActiveSAS)
            is_orphaned = False
            if not is_asr and not is_excluded:
                managed_by_empty = not disk.managed_by or disk.managed_by == ""
                is_unattached = disk.disk_state == 'Unattached'
                is_active_sas = disk.disk_state == 'ActiveSAS'
                
                is_orphaned = (managed_by_empty and not is_active_sas) or (is_unattached and not is_active_sas)
            
            environment_data['resources']['disks'].append({
                'id': disk.id,
                'name': disk.name,
                'resource_group': disk.id.split('/')[4],
                'location': disk.location,
                'disk_state': disk.disk_state,
                'managed_by': disk.managed_by if disk.managed_by else None,
                'is_orphaned': is_orphaned
            })
        
        # Public IPs - check associations (ip_configuration, nat_gateway, public_ip_prefix)
        print("  - Fetching public IPs...")
        for pip in network_client.public_ip_addresses.list_all():
            has_ip_config = pip.ip_configuration is not None
            has_nat = pip.nat_gateway is not None
            has_prefix = pip.public_ip_prefix is not None
            
            environment_data['resources']['public_ips'].append({
                'id': pip.id,
                'name': pip.name,
                'resource_group': pip.id.split('/')[4],
                'location': pip.location,
                'sku': pip.sku.name if pip.sku else None,
                'allocation_method': pip.public_ip_allocation_method,
                'is_orphaned': not has_ip_config and not has_nat and not has_prefix
            })
        
        # Network Interfaces - check VM attachment (exclude NetApp, private endpoints, private link)
        print("  - Fetching network interfaces...")
        for nic in network_client.network_interfaces.list_all():
            # Exclude NetApp volumes, private endpoints, private link services
            has_private_endpoint = nic.private_endpoint is not None
            has_private_link = nic.private_link_service is not None
            has_hosted_workloads = nic.hosted_workloads and len(nic.hosted_workloads) > 0
            has_vm = nic.virtual_machine is not None
            
            is_orphaned = not has_private_endpoint and not has_private_link and not has_hosted_workloads and not has_vm
            
            environment_data['resources']['network_interfaces'].append({
                'id': nic.id,
                'name': nic.name,
                'resource_group': nic.id.split('/')[4],
                'location': nic.location,
                'is_orphaned': is_orphaned
            })
        
        # Network Security Groups - check associations
        print("  - Fetching NSGs...")
        for nsg in network_client.network_security_groups.list_all():
            has_association = (nsg.network_interfaces and len(nsg.network_interfaces) > 0) or \
                            (nsg.subnets and len(nsg.subnets) > 0)
            environment_data['resources']['network_security_groups'].append({
                'id': nsg.id,
                'name': nsg.name,
                'resource_group': nsg.id.split('/')[4],
                'location': nsg.location,
                'network_interfaces_count': len(nsg.network_interfaces) if nsg.network_interfaces else 0,
                'subnets_count': len(nsg.subnets) if nsg.subnets else 0,
                'is_orphaned': not has_association
            })
        
        # Route Tables - check subnet associations
        print("  - Fetching route tables...")
        for rt in network_client.route_tables.list_all():
            environment_data['resources']['route_tables'].append({
                'id': rt.id,
                'name': rt.name,
                'resource_group': rt.id.split('/')[4],
                'location': rt.location,
                'subnets_count': len(rt.subnets) if rt.subnets else 0,
                'is_orphaned': not rt.subnets or len(rt.subnets) == 0
            })
        
        # Load Balancers - check backend pools AND inbound NAT rules
        print("  - Fetching load balancers...")
        for lb in network_client.load_balancers.list_all():
            has_backend_pools = lb.backend_address_pools and len(lb.backend_address_pools) > 0
            has_nat_rules = lb.inbound_nat_rules and len(lb.inbound_nat_rules) > 0
            
            environment_data['resources']['load_balancers'].append({
                'id': lb.id,
                'name': lb.name,
                'resource_group': lb.id.split('/')[4],
                'location': lb.location,
                'sku': lb.sku.name if lb.sku else None,
                'is_orphaned': not has_backend_pools and not has_nat_rules
            })
        
        # Front Door WAF Policies - without Security Policy Links
        print("  - Fetching Front Door WAF policies...")
        for rg in resource_client.resource_groups.list():
            try:
                for waf in frontdoor_client.policies.list(rg.name):
                    # Check if the policy has security policy links (attached to Front Door profiles)
                    has_security_links = waf.security_policy_links and len(waf.security_policy_links) > 0
                    
                    environment_data['resources']['frontdoor_waf_policies'].append({
                        'id': waf.id,
                        'name': waf.name,
                        'resource_group': rg.name,
                        'location': waf.location,
                        'sku': waf.sku.name if waf.sku else None,
                        'is_orphaned': not has_security_links
                    })
            except:
                pass
        
        # Traffic Manager Profiles - without endpoints
        print("  - Fetching Traffic Manager profiles...")
        try:
            from azure.mgmt.trafficmanager import TrafficManagerManagementClient
            tm_client = TrafficManagerManagementClient(credential, subscription_id)
            
            for tm in tm_client.profiles.list_by_subscription():
                has_endpoints = tm.endpoints and len(tm.endpoints) > 0
                
                environment_data['resources']['traffic_manager_profiles'].append({
                    'id': tm.id,
                    'name': tm.name,
                    'resource_group': tm.id.split('/')[4],
                    'location': tm.location,
                    'is_orphaned': not has_endpoints
                })
        except ImportError:
            print("    Warning: azure-mgmt-trafficmanager not installed, skipping Traffic Manager Profiles")
        except Exception as e:
            print(f"    Warning: Could not fetch Traffic Manager Profiles: {e}")
        
        # Application Gateways - check for backend targets (IPs or addresses)
        print("  - Fetching application gateways...")
        for ag in network_client.application_gateways.list_all():
            # Check if any backend pool has backend IP configurations or addresses
            has_targets = False
            if ag.backend_address_pools:
                for pool in ag.backend_address_pools:
                    backend_ips = pool.backend_ip_configurations and len(pool.backend_ip_configurations) > 0
                    backend_addrs = pool.backend_addresses and len(pool.backend_addresses) > 0
                    if backend_ips or backend_addrs:
                        has_targets = True
                        break
            
            environment_data['resources']['application_gateways'].append({
                'id': ag.id,
                'name': ag.name,
                'resource_group': ag.id.split('/')[4],
                'location': ag.location,
                'sku': f"{ag.sku.name}/{ag.sku.tier}" if ag.sku else None,
                'is_orphaned': not has_targets
            })
        
        # Virtual Networks - VNets without subnets
        print("  - Fetching virtual networks...")
        for vnet in network_client.virtual_networks.list_all():
            has_subnets = vnet.subnets and len(vnet.subnets) > 0
            
            environment_data['resources']['virtual_networks'].append({
                'id': vnet.id,
                'name': vnet.name,
                'resource_group': vnet.id.split('/')[4],
                'location': vnet.location,
                'is_orphaned': not has_subnets
            })
            
            # Process subnets within this VNet
            if vnet.subnets:
                for subnet in vnet.subnets:
                    # Check for connected devices (NICs, private endpoints, etc.)
                    has_devices = (
                        (subnet.ip_configurations and len(subnet.ip_configurations) > 0) or
                        (subnet.private_endpoints and len(subnet.private_endpoints) > 0)
                    )
                    
                    # Check for delegation to Azure services
                    has_delegation = subnet.delegations and len(subnet.delegations) > 0
                    
                    environment_data['resources']['subnets'].append({
                        'id': subnet.id,
                        'name': subnet.name,
                        'vnet_name': vnet.name,
                        'resource_group': vnet.id.split('/')[4],
                        'address_prefix': subnet.address_prefix,
                        'is_orphaned': not has_devices and not has_delegation
                    })
        
        # IP Groups - not attached to any Azure Firewall
        print("  - Fetching IP groups...")
        for ip_group in network_client.ip_groups.list():
            # Check if attached to any firewall or firewall policy
            has_firewalls = ip_group.firewalls and len(ip_group.firewalls) > 0
            has_firewall_policies = ip_group.firewall_policies and len(ip_group.firewall_policies) > 0
            
            environment_data['resources']['ip_groups'].append({
                'id': ip_group.id,
                'name': ip_group.name,
                'resource_group': ip_group.id.split('/')[4],
                'location': ip_group.location,
                'is_orphaned': not has_firewalls and not has_firewall_policies
            })
        
        # Private DNS Zones - without Virtual Network Links
        print("  - Fetching private DNS zones...")
        try:
            from azure.mgmt.privatedns import PrivateDnsManagementClient
            privatedns_client = PrivateDnsManagementClient(credential, subscription_id)
            
            for zone in privatedns_client.private_zones.list():
                # Check for virtual network links
                rg_name = zone.id.split('/')[4]
                vnet_links = list(privatedns_client.virtual_network_links.list(rg_name, zone.name))
                has_links = len(vnet_links) > 0
                
                environment_data['resources']['private_dns_zones'].append({
                    'id': zone.id,
                    'name': zone.name,
                    'resource_group': rg_name,
                    'location': zone.location,
                    'is_orphaned': not has_links
                })
        except ImportError:
            print("    Warning: azure-mgmt-privatedns not installed, skipping Private DNS Zones")
        except Exception as e:
            print(f"    Warning: Could not fetch Private DNS Zones: {e}")
        
        # Private Endpoints - not connected to any resource
        print("  - Fetching private endpoints...")
        for pe in network_client.private_endpoints.list_by_subscription():
            # Check if connected to a resource via private link service connection
            has_connection = False
            if pe.private_link_service_connections:
                for conn in pe.private_link_service_connections:
                    if conn.private_link_service_connection_state and \
                       conn.private_link_service_connection_state.status == 'Approved':
                        has_connection = True
                        break
            
            if not has_connection and pe.manual_private_link_service_connections:
                for conn in pe.manual_private_link_service_connections:
                    if conn.private_link_service_connection_state and \
                       conn.private_link_service_connection_state.status == 'Approved':
                        has_connection = True
                        break
            
            environment_data['resources']['private_endpoints'].append({
                'id': pe.id,
                'name': pe.name,
                'resource_group': pe.id.split('/')[4],
                'location': pe.location,
                'is_orphaned': not has_connection
            })
        
        # Virtual Network Gateways - without P2S configuration or connections
        print("  - Fetching virtual network gateways...")
        for rg in resource_client.resource_groups.list():
            try:
                for vng in network_client.virtual_network_gateways.list(rg.name):
                    # Check for Point-to-Site configuration
                    has_p2s = vng.vpn_client_configuration is not None
                    
                    # Check for connections (Site-to-Site, VNet-to-VNet, ExpressRoute)
                    connections = list(network_client.virtual_network_gateway_connections.list(rg.name))
                    has_connections = any(
                        conn.virtual_network_gateway1 and conn.virtual_network_gateway1.id == vng.id or
                        conn.virtual_network_gateway2 and conn.virtual_network_gateway2.id == vng.id
                        for conn in connections
                    )
                    
                    environment_data['resources']['virtual_network_gateways'].append({
                        'id': vng.id,
                        'name': vng.name,
                        'resource_group': rg.name,
                        'location': vng.location,
                        'gateway_type': vng.gateway_type,
                        'vpn_type': vng.vpn_type if hasattr(vng, 'vpn_type') else None,
                        'is_orphaned': not has_p2s and not has_connections
                    })
            except:
                pass
        
        # DDoS Protection Plans - without associated Virtual Networks
        print("  - Fetching DDoS protection plans...")
        for ddos in network_client.ddos_protection_plans.list():
            # Check if any VNets are associated with this DDoS plan
            has_vnets = ddos.virtual_networks and len(ddos.virtual_networks) > 0
            
            environment_data['resources']['ddos_protection_plans'].append({
                'id': ddos.id,
                'name': ddos.name,
                'resource_group': ddos.id.split('/')[4],
                'location': ddos.location,
                'is_orphaned': not has_vnets
            })
        
        # API Connections - not related to any Logic App
        print("  - Fetching API connections...")
        try:
            # API Connections are Microsoft.Web/connections resources
            api_connections = [r for r in resource_client.resources.list() 
                             if r.type == 'Microsoft.Web/connections']
            
            for conn in api_connections:
                rg_name = conn.id.split('/')[4]
                
                # Check if connection is referenced by any Logic App
                # Logic Apps reference connections via their properties
                has_logic_app = False
                try:
                    # Get all Logic Apps in the same resource group
                    logic_apps = [r for r in resource_client.resources.list_by_resource_group(rg_name)
                                if r.type == 'Microsoft.Logic/workflows']
                    
                    # Check if this connection is referenced (simplified check)
                    # Full check would require getting Logic App definition and parsing parameters/connections
                    # For now, we'll check if there are any Logic Apps in the same resource group
                    has_logic_app = len(logic_apps) > 0
                except:
                    pass
                
                environment_data['resources']['api_connections'].append({
                    'id': conn.id,
                    'name': conn.name,
                    'resource_group': rg_name,
                    'location': conn.location,
                    'is_orphaned': not has_logic_app
                })
        except Exception as e:
            print(f"    Warning: Could not fetch API Connections: {e}")
        
        # Certificates - expired certificates (App Service certificates)
        print("  - Fetching certificates...")
        try:
            # Get App Service certificates (Microsoft.Web/certificates)
            certificates = [r for r in resource_client.resources.list()
                          if r.type == 'Microsoft.Web/certificates']
            
            for cert in certificates:
                rg_name = cert.id.split('/')[4]
                
                try:
                    # Get certificate details to check expiration
                    cert_details = web_client.certificates.get(rg_name, cert.name)
                    
                    is_expired = False
                    if cert_details.expiration_date:
                        # Check if certificate is expired
                        is_expired = cert_details.expiration_date < datetime.now(cert_details.expiration_date.tzinfo)
                    
                    environment_data['resources']['certificates'].append({
                        'id': cert.id,
                        'name': cert.name,
                        'resource_group': rg_name,
                        'location': cert.location,
                        'expiration_date': cert_details.expiration_date.isoformat() if cert_details.expiration_date else None,
                        'issuer': cert_details.issuer if hasattr(cert_details, 'issuer') else None,
                        'is_orphaned': is_expired
                    })
                except Exception as e:
                    print(f"    Warning: Could not get details for certificate {cert.name}: {e}")
                    # Add with unknown expiration status
                    environment_data['resources']['certificates'].append({
                        'id': cert.id,
                        'name': cert.name,
                        'resource_group': rg_name,
                        'location': cert.location,
                        'is_orphaned': False  # Default to not orphaned if we can't check
                    })
        except Exception as e:
            print(f"    Warning: Could not fetch Certificates: {e}")
        
        # Availability Sets - check for VMs (exclude ASR availability sets)
        print("  - Fetching availability sets...")
        for rg in resource_client.resource_groups.list():
            try:
                for avset in compute_client.availability_sets.list(rg.name):
                    # Exclude ASR availability sets (end with "-asr")
                    is_asr = avset.name.lower().endswith("-asr")
                    has_vms = avset.virtual_machines and len(avset.virtual_machines) > 0
                    
                    environment_data['resources']['availability_sets'].append({
                        'id': avset.id,
                        'name': avset.name,
                        'resource_group': avset.id.split('/')[4],
                        'location': avset.location,
                        'is_orphaned': not is_asr and not has_vms
                    })
            except:
                pass
        
        # NAT Gateways - not attached to any subnet
        print("  - Fetching NAT gateways...")
        for nat in network_client.nat_gateways.list_all():
            has_subnets = nat.subnets and len(nat.subnets) > 0
            
            environment_data['resources']['nat_gateways'].append({
                'id': nat.id,
                'name': nat.name,
                'resource_group': nat.id.split('/')[4],
                'location': nat.location,
                'sku': f"{nat.sku.name}/{nat.sku.tier}" if nat.sku else None,
                'is_orphaned': not has_subnets
            })
        
        # App Service Plans - without hosting Apps
        # Note: number_of_sites property is unreliable, so we count apps manually
        print("  - Fetching App Service plans...")
        
        # First, get all web apps and group by plan ID
        print("    Fetching all web apps...")
        all_apps = list(web_client.web_apps.list())
        apps_by_plan = {}
        for app in all_apps:
            if app.server_farm_id:
                plan_id = app.server_farm_id.lower()
                apps_by_plan[plan_id] = apps_by_plan.get(plan_id, 0) + 1
        
        # Now check each plan
        print("    Analyzing App Service plans...")
        try:
            for plan in web_client.app_service_plans.list():
                plan_id_lower = plan.id.lower()
                num_apps = apps_by_plan.get(plan_id_lower, 0)
                
                environment_data['resources']['app_service_plans'].append({
                    'id': plan.id,
                    'name': plan.name,
                    'resource_group': plan.id.split('/')[4],
                    'location': plan.location,
                    'sku_name': plan.sku.name if plan.sku else None,
                    'sku_tier': plan.sku.tier if plan.sku else None,
                    'sku_size': plan.sku.size if plan.sku else None,
                    'sku_family': plan.sku.family if plan.sku else None,
                    'sku_capacity': plan.sku.capacity if plan.sku else 1,
                    'kind': plan.kind if plan.kind else 'app',
                    'reserved': plan.reserved if hasattr(plan, 'reserved') else False,
                    'num_apps': num_apps,
                    'is_orphaned': num_apps == 0
                })
        except Exception as e:
            print(f"    Error fetching App Service Plans: {e}")
            pass
        
        # SQL Servers and Elastic Pools
        print("  - Fetching SQL servers...")
        for server in sql_client.servers.list():
            rg = server.id.split('/')[4]
            try:
                pools = list(sql_client.elastic_pools.list_by_server(rg, server.name))
                for pool in pools:
                    databases = list(sql_client.databases.list_by_elastic_pool(rg, server.name, pool.name))
                    environment_data['resources']['sql_servers'].append({
                        'id': pool.id,
                        'name': f"{server.name}/{pool.name}",
                        'type': 'elastic_pool',
                        'resource_group': rg,
                        'location': pool.location,
                        'databases_count': len(databases),
                        'is_orphaned': len(databases) == 0
                    })
            except:
                pass
        
        # Resource Groups - check if empty
        print("  - Fetching resource groups...")
        for rg in resource_client.resource_groups.list():
            rg_resources = list(resource_client.resources.list_by_resource_group(rg.name))
            environment_data['resources']['resource_groups'].append({
                'id': rg.id,
                'name': rg.name,
                'location': rg.location,
                'resources_count': len(rg_resources),
                'is_orphaned': len(rg_resources) == 0
            })
        
        print("Download complete!")
        return environment_data
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


def detect_orphaned_resources(environment_file=None):
    """Detect orphaned Azure resources from JSON file with detailed properties"""
    try:
        if not environment_file:
            return {'error': 'Environment JSON file is required'}
            
        # Load from JSON file
        with open(environment_file, 'r') as f:
            env_data = json.load(f)
        
        resources = env_data['resources']
        
        # Count orphaned resources using the is_orphaned flag from detailed download
        orphaned_counts = {
            'app_service_plans': sum(1 for r in resources.get('app_service_plans', []) if r.get('is_orphaned')),
            'availability_sets': sum(1 for r in resources.get('availability_sets', []) if r.get('is_orphaned')),
            'disks': sum(1 for r in resources.get('disks', []) if r.get('is_orphaned')),
            'sql_elastic_pools': sum(1 for r in resources.get('sql_servers', []) if r.get('is_orphaned')),
            'public_ips': sum(1 for r in resources.get('public_ips', []) if r.get('is_orphaned')),
            'network_interfaces': sum(1 for r in resources.get('network_interfaces', []) if r.get('is_orphaned')),
            'network_security_groups': sum(1 for r in resources.get('network_security_groups', []) if r.get('is_orphaned')),
            'route_tables': sum(1 for r in resources.get('route_tables', []) if r.get('is_orphaned')),
            'load_balancers': sum(1 for r in resources.get('load_balancers', []) if r.get('is_orphaned')),
            'frontdoor_waf_policies': sum(1 for r in resources.get('frontdoor_waf_policies', []) if r.get('is_orphaned')),
            'traffic_manager_profiles': sum(1 for r in resources.get('traffic_manager_profiles', []) if r.get('is_orphaned')),
            'application_gateways': sum(1 for r in resources.get('application_gateways', []) if r.get('is_orphaned')),
            'virtual_networks': sum(1 for r in resources.get('virtual_networks', []) if r.get('is_orphaned')),
            'subnets': sum(1 for r in resources.get('subnets', []) if r.get('is_orphaned')),
            'ip_groups': sum(1 for r in resources.get('ip_groups', []) if r.get('is_orphaned')),
            'private_dns_zones': sum(1 for r in resources.get('private_dns_zones', []) if r.get('is_orphaned')),
            'private_endpoints': sum(1 for r in resources.get('private_endpoints', []) if r.get('is_orphaned')),
            'virtual_network_gateways': sum(1 for r in resources.get('virtual_network_gateways', []) if r.get('is_orphaned')),
            'ddos_protection_plans': sum(1 for r in resources.get('ddos_protection_plans', []) if r.get('is_orphaned')),
            'api_connections': sum(1 for r in resources.get('api_connections', []) if r.get('is_orphaned')),
            'certificates': sum(1 for r in resources.get('certificates', []) if r.get('is_orphaned')),
            'nat_gateways': sum(1 for r in resources.get('nat_gateways', []) if r.get('is_orphaned')),
            'resource_groups': sum(1 for r in resources.get('resource_groups', []) if r.get('is_orphaned'))
        }
        
        return orphaned_counts
        
    except Exception as e:
        return {'error': str(e)}


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def home():
    """Home page with resource type selector"""
    return render_template('home.html', resource_types=RESOURCE_TYPES)

@app.route('/overview')
def overview():
    """Overview page for environment analysis"""
    return render_template('overview.html')

@app.route('/api/download-environment')
def api_download_environment():
    """API endpoint to download Azure environment as JSON"""
    try:
        # Check if demo mode is enabled
        demo_mode = request.args.get('demo', 'false').lower() == 'true'
        
        if demo_mode:
            # Generate demo data instead of real Azure scan
            import random
            from demo_data_generator import generate_wasteful_environment
            # Randomize resource count between 800-1500 for variety
            target_resources = random.randint(800, 1500)
            env_data = generate_wasteful_environment(target_resources=target_resources)
        else:
            # Real Azure scan
            env_data = download_azure_environment()
            
            if 'error' in env_data:
                return jsonify(env_data), 500
        
        # Save to file
        data_dir = app.config['ENVIRONMENT_FOLDER']
        os.makedirs(data_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Use appropriate filename with clear mode identification
        if is_demo_mode():
            filename = f'azure_scan_demo_{timestamp}.json'
        else:
            filename = f'azure_scan_production_{timestamp}.json'
        
        filepath = os.path.join(data_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(env_data, f, indent=2)
        
        # Count total resources across all types
        total_resources = sum(len(v) for v in env_data['resources'].values() if isinstance(v, list))
        
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'resource_count': total_resources,
            'demo_mode': demo_mode
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/demo-mode', methods=['GET', 'POST'])
def demo_mode_toggle():
    """Get or set demo mode status"""
    if request.method == 'POST':
        data = request.json
        session['demo_mode'] = data.get('enabled', False)
        return jsonify({'success': True, 'demo_mode': session.get('demo_mode', False)})
    else:
        return jsonify({'demo_mode': session.get('demo_mode', False)})

@app.route('/api/scan-files')
def get_scan_files():
    """API endpoint to list all available scan files"""
    try:
        data_dir = app.config['ENVIRONMENT_FOLDER']
        
        # Filter files based on environment
        if is_demo_mode():
            # In dev mode, only show dev files
            json_files = [f for f in os.listdir(data_dir) if f.startswith(DEV_FILE_PREFIX) and f.endswith('.json')]
        else:
            # In production, only show non-dev files
            json_files = [f for f in os.listdir(data_dir) 
                         if f.startswith(PROD_FILE_PREFIX) and f.endswith('.json') 
                         and not f.startswith(DEV_FILE_PREFIX)]
        
        scan_files = []
        for filename in json_files:
            filepath = os.path.join(data_dir, filename)
            file_stats = os.stat(filepath)
            file_size = file_stats.st_size
            
            # Try to read resource count from file
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    resource_count = sum(len(v) for v in data.get('resources', {}).values() if isinstance(v, list))
                    scan_date = data.get('timestamp', 'Unknown')
            except:
                resource_count = 0
                scan_date = 'Unknown'
            
            scan_files.append({
                'filename': filename,
                'size': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'modified': datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'resource_count': resource_count,
                'scan_date': scan_date
            })
        
        # Sort by modified date, newest first
        scan_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'files': scan_files,
            'total_count': len(scan_files),
            'total_size_mb': round(sum(f['size'] for f in scan_files) / (1024 * 1024), 2),
            'dev_mode': is_demo_mode()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-scan/<filename>', methods=['DELETE'])
def delete_scan_file(filename):
    """API endpoint to delete a specific scan file"""
    try:
        # Prevent deletion of demo files
        if filename.startswith(DEV_FILE_PREFIX):
            return jsonify({'error': 'Cannot delete demo files'}), 403
        
        # Security check: ensure filename is valid (allow new and old naming formats)
        valid_prefixes = ('azure_scan_production_', 'azure_scan_demo_', 'azure_environment_')
        if not any(filename.startswith(prefix) for prefix in valid_prefixes) or not filename.endswith('.json'):
            return jsonify({'error': 'Invalid filename'}), 400
        
        data_dir = app.config['ENVIRONMENT_FOLDER']
        filepath = os.path.join(data_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': f'Scan file {filename} deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-all-scans', methods=['DELETE'])
def delete_all_scans():
    """API endpoint to delete all scan files"""
    try:
        data_dir = app.config['ENVIRONMENT_FOLDER']
        
        # In demo mode, cannot delete demo files; in production, only delete production files
        if is_demo_mode():
            return jsonify({'error': 'Cannot delete demo files'}), 403
        
        # Only delete production files (not demo files)
        json_files = [f for f in os.listdir(data_dir) 
                     if f.startswith(PROD_FILE_PREFIX) and f.endswith('.json') 
                     and not f.startswith(DEV_FILE_PREFIX)]
        
        deleted_count = 0
        for filename in json_files:
            filepath = os.path.join(data_dir, filename)
            os.remove(filepath)
            deleted_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} scan file(s)',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orphaned-resources')
def get_orphaned_resources():
    """API endpoint to get orphaned resources count from local JSON file"""
    try:
        # Find the latest environment JSON file
        data_dir = app.config['ENVIRONMENT_FOLDER']
        
        # Filter files based on environment
        if is_demo_mode():
            json_files = [f for f in os.listdir(data_dir) if f.startswith(DEV_FILE_PREFIX) and f.endswith('.json')]
        else:
            json_files = [f for f in os.listdir(data_dir) 
                         if f.startswith(PROD_FILE_PREFIX) and f.endswith('.json') 
                         and not f.startswith(DEV_FILE_PREFIX)]
        
        if not json_files:
            return jsonify({'error': 'No environment data found. Please download environment first.'}), 404
        
        # Get the most recent file
        latest_file = max([os.path.join(data_dir, f) for f in json_files], key=os.path.getmtime)
        
        orphaned_data = detect_orphaned_resources(environment_file=latest_file)
        return jsonify(orphaned_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/complete-resources')
def get_complete_resources():
    """API endpoint to get complete resource counts (total, active, orphaned) from local JSON file"""
    try:
        # Find the latest environment JSON file
        data_dir = app.config['ENVIRONMENT_FOLDER']
        
        # Filter files based on environment
        if is_demo_mode():
            json_files = [f for f in os.listdir(data_dir) if f.startswith(DEV_FILE_PREFIX) and f.endswith('.json')]
        else:
            json_files = [f for f in os.listdir(data_dir) 
                         if f.startswith(PROD_FILE_PREFIX) and f.endswith('.json') 
                         and not f.startswith(DEV_FILE_PREFIX)]
        
        if not json_files:
            return jsonify({'error': 'No environment data found. Please download environment first.'}), 404
        
        # Get the most recent file
        latest_file = max([os.path.join(data_dir, f) for f in json_files], key=os.path.getmtime)
        
        with open(latest_file, 'r') as f:
            scan_data = json.load(f)
        
        # Get the resources object from scan data
        resources = scan_data.get('resources', {})
        
        # Get orphaned counts
        orphaned_data = detect_orphaned_resources(environment_file=latest_file)
        
        # Build complete resource view data
        complete_view = {}
        
        resource_mapping = {
            'app_service_plans': 'app_service_plans',
            'availability_sets': 'availability_sets',
            'disks': 'disks',
            'sql_elastic_pools': 'sql_servers',  # SQL elastic pools are tracked under sql_servers
            'public_ips': 'public_ips',
            'network_interfaces': 'network_interfaces',
            'network_security_groups': 'network_security_groups',
            'route_tables': 'route_tables',
            'load_balancers': 'load_balancers',
            'frontdoor_waf_policies': 'frontdoor_waf_policies',
            'traffic_manager_profiles': 'traffic_manager_profiles',
            'application_gateways': 'application_gateways',
            'virtual_networks': 'virtual_networks',
            'subnets': 'subnets',
            'nat_gateways': 'nat_gateways',
            'ip_groups': 'ip_groups',
            'private_dns_zones': 'private_dns_zones',
            'private_endpoints': 'private_endpoints',
            'virtual_network_gateways': 'virtual_network_gateways',
            'ddos_protection_plans': 'ddos_protection_plans',
            'storage_accounts': 'resource_groups',  # Using resource_groups as proxy
            'certificates': 'certificates'
        }
        
        for key, scan_key in resource_mapping.items():
            # Get total count from scan data resources
            total = len(resources.get(scan_key, []))
            
            complete_view[key] = {
                'total': total
            }
        
        return jsonify(complete_view)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/resource-availability')
def get_resource_availability():
    """API endpoint to check which resource types have data in the latest scan"""
    try:
        # Find the latest environment JSON file
        data_dir = app.config['ENVIRONMENT_FOLDER']
        
        # Filter files based on environment
        if is_demo_mode():
            json_files = [f for f in os.listdir(data_dir) if f.startswith(DEV_FILE_PREFIX) and f.endswith('.json')]
        else:
            json_files = [f for f in os.listdir(data_dir) 
                         if f.startswith(PROD_FILE_PREFIX) and f.endswith('.json') 
                         and not f.startswith(DEV_FILE_PREFIX)]
        
        if not json_files:
            return jsonify({'error': 'No scan data', 'availability': {}})
        
        # Load latest JSON scan
        latest_file = max([os.path.join(data_dir, f) for f in json_files], key=os.path.getmtime)
        
        with open(latest_file, 'r') as f:
            scan_data = json.load(f)
        
        # Map resource type to JSON key
        resource_key_mapping = {
            'app-service': 'app_service_plans',
            'sql-databases': 'sql_servers',
            'virtual-machines': 'virtual_machines',
            'public-ips': 'public_ips',
            'disks': 'disks',
            'nics': 'network_interfaces',
            'load-balancers': 'load_balancers',
            'availability-sets': 'availability_sets',
            'route-tables': 'route_tables',
            'nat-gateways': 'nat_gateways',
            'frontdoor-waf': 'frontdoor_waf_policies',
            'traffic-manager': 'traffic_manager_profiles',
            'subnets': 'subnets',
            'ip-groups': 'ip_groups',
            'private-dns': 'private_dns_zones',
            'private-endpoints': 'private_endpoints',
            'vnet-gateways': 'virtual_network_gateways',
            'ddos-plans': 'ddos_protection_plans',
            'api-connections': 'api_connections',
            'certificates': 'certificates',
            'storage-accounts': 'storage_accounts',
            'nsgs': 'network_security_groups'
        }
        
        availability = {}
        resources = scan_data.get('resources', {})
        
        for resource_type, json_key in resource_key_mapping.items():
            data = resources.get(json_key, [])
            availability[resource_type] = {
                'has_data': len(data) > 0,
                'count': len(data),
                'orphaned_count': len([r for r in data if r.get('is_orphaned', False)])
            }
        
        return jsonify({
            'scan_file': os.path.basename(latest_file),
            'scan_date': scan_data.get('timestamp', 'Unknown'),
            'availability': availability
        })
    except Exception as e:
        return jsonify({'error': str(e), 'availability': {}}), 500

@app.route('/api/orphaned-resources/details')
def get_orphaned_resources_details():
    """API endpoint to get detailed orphaned resources with names, resource groups, and locations"""
    try:
        # Find the latest environment JSON file
        data_dir = app.config['ENVIRONMENT_FOLDER']
        
        # Filter files based on environment
        if is_demo_mode():
            json_files = [f for f in os.listdir(data_dir) if f.startswith(DEV_FILE_PREFIX) and f.endswith('.json')]
        else:
            json_files = [f for f in os.listdir(data_dir) 
                         if f.startswith(PROD_FILE_PREFIX) and f.endswith('.json') 
                         and not f.startswith(DEV_FILE_PREFIX)]
        
        if not json_files:
            return jsonify({'error': 'No environment data found. Please download environment first.'}), 404
        
        # Get the most recent file
        latest_file = max([os.path.join(data_dir, f) for f in json_files], key=os.path.getmtime)
        
        # Load from JSON file
        with open(latest_file, 'r') as f:
            env_data = json.load(f)
        
        resources = env_data['resources']
        
        # Get detailed orphaned resources
        detailed_orphaned = {}
        
        # NOTE: Cost calculations require Azure Cost Management API integration
        # Fictional cost estimates have been removed to maintain data integrity
        
        for resource_type, resources_list in resources.items():
            orphaned = [r for r in resources_list if r.get('is_orphaned')]
            if orphaned:
                detailed_orphaned[resource_type] = {
                    'count': len(orphaned),
                    'resources': [
                        {
                            'name': r.get('name', 'N/A'),
                            'resource_group': r.get('resource_group', 'N/A'),
                            'location': r.get('location', 'N/A'),
                            'id': r.get('id', '')
                        }
                        for r in orphaned
                    ]
                }
        
        return jsonify(detailed_orphaned)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze/<resource_type>')
def analyze(resource_type):
    """Analysis dashboard for specific resource type"""
    if resource_type not in RESOURCE_TYPES:
        return redirect(url_for('home'))
    
    # Use generic dashboard for all resource types
    return render_template('generic_dashboard.html', 
                         resource_type=resource_type,
                         resource_info=RESOURCE_TYPES[resource_type])

def analyze_generic_resource_type(resource_type, resources_data):
    """Generic analyzer for any resource type from JSON data with enhanced insights"""
    
    if not resources_data:
        # Return empty but valid response instead of error
        resource_name = RESOURCE_TYPES.get(resource_type, {}).get("name", "resources")
        return {
            'summary': {
                'total_resources': 0,
                'orphaned_count': 0,
                'active_count': 0,
                'orphaned_percentage': 0
            },
            'cost_impact': {
                'monthly_waste': 0,
                'annual_savings': 0,
                'quick_wins': []
            },
            'risk_assessment': {'level': 'None', 'items': []},
            'action_priorities': {'urgent': [], 'high': [], 'low': []},
            'recommendations': [],
            'location_stats': [],
            'resource_group_stats': [],
            'orphaned_resources': [],
            'resource_details': [],
            'info_message': f'No {resource_name} found in your Azure environment. This is normal if you don\'t use this resource type.'
        }
    
    # NOTE: Actual costs require Azure Cost Management API integration
    # Cost calculations are disabled to avoid showing fictional data
    cost_per_resource = 0
    
    total_resources = len(resources_data)
    orphaned_resources = [r for r in resources_data if r.get('is_orphaned', False)]
    active_resources = [r for r in resources_data if not r.get('is_orphaned', False)]
    
    # Cost calculations disabled - requires Azure Cost Management integration
    monthly_waste = 0
    annual_savings = 0
    
    # Quick wins (based on resource count, not fictional costs)
    quick_wins = []
    if len(orphaned_resources) > 5:
        quick_wins.append({
            'action': f'Delete {len(orphaned_resources)} orphaned {RESOURCE_TYPES.get(resource_type, {}).get("name", "resources")}',
            'savings': 'Cost data requires Azure Cost Management integration'
        })
    
    # Risk Assessment
    risk_level = 'Low'
    risk_items = []
    
    if resource_type in ['nsgs', 'route-tables'] and len(orphaned_resources) > 5:
        risk_level = 'High'
        risk_items.append(f'{len(orphaned_resources)} orphaned network security resources could impact security posture')
    elif resource_type == 'nics' and len(orphaned_resources) > 10:
        risk_level = 'Medium'
        risk_items.append(f'{len(orphaned_resources)} orphaned NICs indicate potential VM cleanup needed')
    elif cost_per_resource == 0 and len(orphaned_resources) > 15:
        risk_level = 'Low'
        risk_items.append(f'{len(orphaned_resources)} orphaned resources (no direct cost, hygiene improvement)')
    
    # Group by location
    location_stats = {}
    for resource in resources_data:
        loc = resource.get('location', 'Unknown')
        if loc not in location_stats:
            location_stats[loc] = {'total': 0, 'orphaned': 0, 'active': 0, 'cost': 0}
        location_stats[loc]['total'] += 1
        if resource.get('is_orphaned'):
            location_stats[loc]['orphaned'] += 1
            location_stats[loc]['cost'] += cost_per_resource
        else:
            location_stats[loc]['active'] += 1
    
    # Group by resource group with performance metrics
    rg_stats = {}
    for resource in resources_data:
        rg = resource.get('resource_group', 'Unknown')
        if rg not in rg_stats:
            rg_stats[rg] = {'total': 0, 'orphaned': 0, 'active': 0, 'orphan_rate': 0}
        rg_stats[rg]['total'] += 1
        if resource.get('is_orphaned'):
            rg_stats[rg]['orphaned'] += 1
        else:
            rg_stats[rg]['active'] += 1
    
    # Calculate orphan rates for benchmarking
    for rg in rg_stats:
        if rg_stats[rg]['total'] > 0:
            rg_stats[rg]['orphan_rate'] = round((rg_stats[rg]['orphaned'] / rg_stats[rg]['total']) * 100, 1)
    
    # Identify best and worst performing RGs
    rg_list = [(rg, stats) for rg, stats in rg_stats.items() if stats['total'] >= 3]
    best_rg = min(rg_list, key=lambda x: x[1]['orphan_rate']) if rg_list else None
    worst_rg = max(rg_list, key=lambda x: x[1]['orphan_rate']) if rg_list else None
    
    # Generate recommendations with enhanced intelligence
    recommendations = generate_enhanced_recommendations(
        resource_type, resources_data, orphaned_resources, 
        cost_per_resource, rg_stats, worst_rg
    )
    
    # Action Priority Matrix
    action_priorities = {
        'urgent': [],  # >$500/month or critical security
        'high': [],    # $100-$500/month or significant waste
        'low': []      # <$100/month or hygiene
    }
    
    for rec in recommendations:
        priority_level = rec.get('priority', 'Low')
        action_item = {
            'title': rec['resource'],
            'action': rec['suggestion'],
            'savings': rec.get('potential_saving', 'N/A')
        }
        
        if priority_level == 'Critical':
            action_priorities['urgent'].append(action_item)
        elif priority_level == 'High':
            action_priorities['high'].append(action_item)
        else:
            action_priorities['low'].append(action_item)
    
    # Internal Benchmarks (based on your resource groups)
    avg_orphan_rate = round((len(orphaned_resources) / total_resources * 100) if total_resources > 0 else 0, 1)
    
    # Calculate average across all resource groups for internal comparison
    rg_orphan_rates = [stats['orphan_rate'] for stats in rg_stats.values() if stats['total'] >= 3]
    avg_rg_orphan_rate = round(sum(rg_orphan_rates) / len(rg_orphan_rates), 1) if rg_orphan_rates else avg_orphan_rate
    
    benchmarks = {
        'your_orphan_rate': avg_orphan_rate,
        'avg_rg_orphan_rate': avg_rg_orphan_rate,
        'best_rg': {'name': best_rg[0], 'rate': best_rg[1]['orphan_rate']} if best_rg else None,
        'worst_rg': {'name': worst_rg[0], 'rate': worst_rg[1]['orphan_rate']} if worst_rg else None,
        'total_rg_count': len(rg_stats)
    }
    
    # Prepare enhanced response
    return {
        'summary': {
            'total_resources': total_resources,
            'orphaned_count': len(orphaned_resources),
            'active_count': len(active_resources),
            'orphaned_percentage': avg_orphan_rate
        },
        'cost_impact': {
            'monthly_waste': round(monthly_waste, 2),
            'annual_savings': round(annual_savings, 2),
            'quick_wins': quick_wins
        },
        'risk_assessment': {
            'level': risk_level,
            'items': risk_items
        },
        'action_priorities': action_priorities,
        'benchmarks': benchmarks,
        'recommendations': recommendations,
        'location_stats': [
            {
                'Location': loc, 
                'Total': stats['total'], 
                'Orphaned': stats['orphaned'], 
                'Active': stats['active']
            }
            for loc, stats in sorted(location_stats.items(), key=lambda x: x[1]['orphaned'], reverse=True)
        ],
        'resource_group_stats': [
            {
                'ResourceGroup': rg, 
                'Total': stats['total'], 
                'Orphaned': stats['orphaned'], 
                'Active': stats['active'],
                'OrphanRate': f"{stats['orphan_rate']}%"
            }
            for rg, stats in sorted(rg_stats.items(), key=lambda x: (x[1]['orphaned'], x[1]['orphan_rate']), reverse=True)[:10]
        ],
        'orphaned_resources': [
            {
                'name': r.get('name', 'Unknown'),
                'resource_group': r.get('resource_group', 'Unknown'),
                'location': r.get('location', 'Unknown'),
                'id': r.get('id', '')
            }
            for r in orphaned_resources  # All orphaned resources
        ],
        'resource_details': resources_data[:50]  # Top 50 resources
    }

def generate_enhanced_recommendations(resource_type, all_resources, orphaned_resources, cost_per_resource, rg_stats, worst_rg):
    """Generate recommendations based on resource analysis (without fictional cost estimates)"""
    recommendations = []
    
    if orphaned_resources:
        # Determine priority based on resource type criticality
        if resource_type in ['ddos-plans', 'vnet-gateways', 'application-gateways']:
            priority = 'Critical'
        elif resource_type in ['disks', 'public-ips', 'load-balancers', 'nat-gateways']:
            priority = 'High'
        elif len(orphaned_resources) > 10:
            priority = 'High'
        elif len(orphaned_resources) > 5:
            priority = 'Medium'
        else:
            priority = 'Low'
        
        recommendations.append({
            'type': 'orphaned_cleanup',
            'resource': f"{len(orphaned_resources)} orphaned {RESOURCE_TYPES.get(resource_type, {}).get('name', 'resources')}",
            'current_state': f"{len(orphaned_resources)} unused resources detected",
            'suggestion': f"Review and delete orphaned resources. Start with {min(len(orphaned_resources), 10)} resources",
            'potential_saving': 'Integrate Azure Cost Management for actual cost data',
            'priority': priority,
            'impact': 'Cost reduction opportunity'
        })
    
    # Resource type-specific recommendations (without fictional costs)
    if resource_type == 'sql-databases':
        # Elastic pool optimization
        pools = [r for r in all_resources if 'elastic' in r.get('name', '').lower() or 'pool' in r.get('name', '').lower()]
        if pools:
            recommendations.append({
                'type': 'sql_optimization',
                'resource': f"{len(pools)} SQL Elastic Pools",
                'current_state': "Elastic pools detected",
                'suggestion': "Review DTU/vCore usage over 30 days using Azure Monitor. Downgrade tier if consistently <50% utilized",
                'potential_saving': 'Check Azure Cost Management for actual usage costs',
                'priority': 'High',
                'impact': 'Performance maintained, costs reduced'
            })
        
        # Multiple databases in same region
        by_location = {}
        for r in all_resources:
            loc = r.get('location', 'Unknown')
            by_location[loc] = by_location.get(loc, 0) + 1
        
        high_density_locs = [loc for loc, count in by_location.items() if count > 5]
        if high_density_locs:
            recommendations.append({
                'type': 'sql_consolidation',
                'resource': f"Multiple SQL servers in {len(high_density_locs)} locations",
                'current_state': f"High database count in {', '.join(high_density_locs[:2])}",
                'suggestion': "Consider consolidating databases into elastic pools for better resource utilization",
                'potential_saving': 'Analyze with Azure Cost Management',
                'priority': 'Medium',
                'impact': 'Potential cost reduction for multiple databases'
            })
    
    elif resource_type == 'virtual-machines':
        # Stopped/deallocated VMs
        stopped_vms = [r for r in all_resources if r.get('power_state') in ['stopped', 'deallocated', 'Stopped', 'Deallocated']]
        if stopped_vms:
            recommendations.append({
                'type': 'vm_cleanup',
                'resource': f"{len(stopped_vms)} Stopped/Deallocated VMs",
                'current_state': "VMs stopped but still incurring storage costs",
                'suggestion': "Delete VMs not used in 30+ days. Create disk snapshots if needed for recovery",
                'potential_saving': 'Storage and potential compute costs - check Azure Cost Management',
                'priority': 'High',
                'impact': 'Eliminate waste from unused VMs'
            })
        
        # Auto-shutdown recommendation
        if len(all_resources) > 5:
            recommendations.append({
                'type': 'vm_autoshutdown',
                'resource': f"{len(all_resources)} Virtual Machines",
                'current_state': "Consider implementing auto-shutdown policies",
                'suggestion': "Implement auto-shutdown schedules for dev/test VMs (e.g., 7PM-7AM, weekends)",
                'potential_saving': 'Significant savings for non-production workloads',
                'priority': 'Medium',
                'impact': 'Automated cost control'
            })
    
    elif resource_type == 'disks':
        # Unattached premium disks
        premium_disks = [r for r in orphaned_resources if 'premium' in str(r.get('sku', '')).lower() or 'Premium' in str(r.get('sku', ''))]
        if premium_disks:
            recommendations.append({
                'type': 'premium_disk_cleanup',
                'resource': f"{len(premium_disks)} Unattached Premium Disks",
                'current_state': f"Premium SSD disks not attached to VMs",
                'suggestion': "Create snapshots for backup, then delete. Premium disks cost more than Standard",
                'potential_saving': 'Check actual costs in Azure Cost Management',
                'priority': 'Critical',
                'impact': 'Storage cost reduction'
            })
        
        # Snapshot recommendation
        if len(orphaned_resources) > 3:
            recommendations.append({
                'type': 'disk_snapshot_strategy',
                'resource': f"{len(orphaned_resources)} Unattached Disks",
                'current_state': "Multiple unattached disks detected",
                'suggestion': "Consider incremental snapshots instead of keeping full disks if data retention is needed",
                'potential_saving': 'Snapshots cost less than full disks',
                'priority': 'Medium',
                'impact': 'Backup retained, costs reduced'
            })
    
    elif resource_type == 'public-ips':
        # Static IP optimization
        static_ips = [r for r in orphaned_resources if r.get('allocation_method') == 'Static' or r.get('sku') == 'Standard']
        if static_ips:
            recommendations.append({
                'type': 'static_ip_cleanup',
                'resource': f"{len(static_ips)} Orphaned Static Public IPs",
                'current_state': f"Reserved IPs not associated with any resource",
                'suggestion': "Release orphaned static IPs. Re-create as dynamic when needed if applicable",
                'potential_saving': 'Static IPs incur charges - check Azure Cost Management',
                'priority': 'High',
                'impact': 'Quick cleanup - no impact on active resources'
            })
        
        # Long-term static IP review
        if len(all_resources) > 10:
            recommendations.append({
                'type': 'ip_allocation_review',
                'resource': f"{len(all_resources)} Public IP Addresses",
                'current_state': "Review static vs dynamic allocation strategy",
                'suggestion': "Audit if all IPs need static allocation. Use dynamic for dev/test environments",
                'potential_saving': 'Review allocation patterns',
                'priority': 'Low',
                'impact': 'Ongoing cost optimization'
            })
    
    elif resource_type == 'nat-gateways':
        # Zero-traffic NAT gateways
        if orphaned_resources:
            recommendations.append({
                'type': 'nat_gateway_cleanup',
                'resource': f"{len(orphaned_resources)} Orphaned NAT Gateways",
                'current_state': f"NAT Gateways with no outbound traffic or subnet associations",
                'suggestion': "Delete unused NAT Gateways after verifying no planned usage",
                'potential_saving': 'NAT Gateways have hourly charges - check Azure Cost Management',
                'priority': 'High',
                'impact': 'Cost reduction opportunity'
            })
    
    elif resource_type == 'ddos-plans':
        if orphaned_resources or len(all_resources) > 1:
            recommendations.append({
                'type': 'ddos_consolidation',
                'resource': f"{len(all_resources)} DDoS Protection Plans",
                'current_state': f"DDoS Standard plans are high-cost resources",
                'suggestion': "Consolidate to single plan per region. Verify if Standard tier is truly needed vs Basic (included)",
                'potential_saving': 'DDoS Standard has significant monthly costs - check Azure Cost Management',
                'priority': 'Critical',
                'impact': 'Major cost reduction opportunity'
            })
    
    elif resource_type == 'vnet-gateways':
        if orphaned_resources:
            recommendations.append({
                'type': 'vnet_gateway_cleanup',
                'resource': f"{len(orphaned_resources)} Orphaned VNet Gateways",
                'current_state': "VPN/ExpressRoute gateways not connected to circuits or tunnels",
                'suggestion': "Delete unused VNet Gateways. Can recreate if needed later",
                'potential_saving': 'VNet Gateways have hourly charges - check Azure Cost Management',
                'priority': 'Critical',
                'impact': 'High-cost infrastructure cleanup'
            })
    
    elif resource_type == 'nics':
        if len(orphaned_resources) > 10:
            recommendations.append({
                'type': 'nic_cleanup_investigation',
                'resource': f"{len(orphaned_resources)} Orphaned Network Interfaces",
                'current_state': "High number of orphaned NICs indicates VM cleanup needed",
                'suggestion': "Investigate parent VMs. NICs are free but indicate poor resource hygiene",
                'potential_saving': "No direct cost, but indicates larger cleanup opportunity",
                'priority': 'Medium',
                'impact': 'Environment hygiene and inventory accuracy'
            })
    
    elif resource_type == 'nsgs':
        if len(orphaned_resources) > 5:
            recommendations.append({
                'type': 'nsg_security_review',
                'resource': f"{len(orphaned_resources)} Orphaned Network Security Groups",
                'current_state': "Unattached NSGs pose security review overhead",
                'suggestion': "Delete NSGs not associated with subnets or NICs. Document before deletion",
                'potential_saving': "No direct cost, improves security posture clarity",
                'priority': 'High',
                'impact': 'Security hygiene and compliance'
            })
    
    elif resource_type == 'load-balancers':
        if orphaned_resources:
            recommendations.append({
                'type': 'load_balancer_cleanup',
                'resource': f"{len(orphaned_resources)} Orphaned Load Balancers",
                'current_state': "Load balancers with no backend pools or rules",
                'suggestion': "Delete unused load balancers (Standard tier incurs charges)",
                'potential_saving': 'Check Azure Cost Management for actual costs',
                'priority': 'High',
                'impact': 'Cost reduction + cleaner network architecture'
            })
    
    # Generic consolidation for resource groups with high orphan rates
    if worst_rg and worst_rg[1]['orphan_rate'] > 40:
        recommendations.append({
            'type': 'rg_cleanup_focus',
            'resource': f"Resource Group: {worst_rg[0]}",
            'current_state': f"{worst_rg[1]['orphan_rate']}% orphan rate - highest in your environment",
            'suggestion': f"Priority cleanup: Focus on {worst_rg[0]} with {worst_rg[1]['orphaned']} orphaned resources",
            'potential_saving': 'Target this RG first for maximum impact',
            'priority': 'High',
            'impact': 'Focused cleanup approach'
        })
    
    # Multi-region consolidation
    unique_locations = len(set(r.get('location', '') for r in all_resources))
    if unique_locations > 3 and len(all_resources) > 15:
        recommendations.append({
            'type': 'region_consolidation',
            'resource': f"{len(all_resources)} resources across {unique_locations} regions",
            'current_state': "Resources spread across many Azure regions",
            'suggestion': "Evaluate if all regions are needed. Consolidate to 2-3 primary regions to reduce data transfer costs",
            'potential_saving': 'Reduces data egress charges between regions',
            'priority': 'Low',
            'impact': 'Long-term architecture optimization'
        })
    
    return recommendations

@app.route('/api/data/<resource_type>')
def get_data(resource_type):
    """API endpoint to get analyzed data for specific resource type"""
    
    if resource_type == 'app-service':
        # Check if we should use JSON data (from Azure scan) instead of CSV
        use_json = request.args.get('source') == 'json'
        
        if use_json:
            # Use latest JSON scan data
            environment_dir = app.config['ENVIRONMENT_FOLDER']
            
            # Filter files based on environment
            if is_demo_mode():
                json_files = sorted([f for f in os.listdir(environment_dir) if f.startswith(DEV_FILE_PREFIX) and f.endswith('.json')])
            else:
                json_files = sorted([f for f in os.listdir(environment_dir) 
                                    if f.startswith(PROD_FILE_PREFIX) and f.endswith('.json') 
                                    and not f.startswith(DEV_FILE_PREFIX)])
            
            if not json_files:
                return jsonify({
                    'error': 'no_data',
                    'message': 'No Azure scan data found. Please run a scan from the Overview page first.'
                }), 404
            
            # Load latest JSON scan
            latest_json = json_files[-1]
            json_path = os.path.join(environment_dir, latest_json)
            
            try:
                with open(json_path, 'r') as f:
                    scan_data = json.load(f)
                
                plans_data = scan_data.get('resources', {}).get('app_service_plans', [])
                
                if not plans_data:
                    return jsonify({
                        'error': 'no_data',
                        'message': 'No App Service Plans found in the scan data.'
                    }), 404
                
                # Convert JSON to DataFrame format
                df = convert_json_to_app_service_dataframe(plans_data)
                
                # Parse pricing tiers
                df[['TIER_NAME', 'SKU', 'INSTANCES']] = df['PRICING TIER'].apply(
                    lambda x: pd.Series(parse_pricing_tier(x))
                )
                
                # Run analysis
                total_instances = df['INSTANCES'].sum()
                total_apps = df['APPS'].sum()
                total_plans = len(df)
                
                # Generate all statistics
                tier_stats = df.groupby(['SKU', 'OPERATING SYSTEM']).agg({
                    'NAME': 'count',
                    'APPS': 'sum',
                    'INSTANCES': 'sum'
                }).reset_index()
                tier_stats.columns = ['Tier', 'OS', 'Plans', 'Apps', 'Instances']
                tier_stats = tier_stats.sort_values(['Tier', 'OS'], ascending=[False, True])
                
                location_stats = df.groupby('LOCATION').agg({
                    'NAME': 'count',
                    'APPS': 'sum',
                    'INSTANCES': 'sum'
                }).reset_index()
                location_stats.columns = ['Location', 'Plans', 'Apps', 'Instances']
                location_stats = location_stats.sort_values('Plans', ascending=False)
                
                os_stats = df.groupby('OPERATING SYSTEM').agg({
                    'NAME': 'count',
                    'APPS': 'sum'
                }).reset_index()
                os_stats.columns = ['OS', 'Plans', 'Apps']
                
                rg_stats = df.groupby('RESOURCE GROUP').agg({
                    'NAME': 'count',
                    'APPS': 'sum',
                    'INSTANCES': 'sum'
                }).reset_index()
                rg_stats.columns = ['ResourceGroup', 'Plans', 'Apps', 'Instances']
                rg_stats = rg_stats.sort_values('Plans', ascending=False).head(10)
                
                # Identify orphaned plans (plans with 0 apps)
                orphaned_plans = df[df['APPS'] == 0]
                active_plans = df[df['APPS'] > 0]
                
                # Generate recommendations
                recommendations = generate_app_service_recommendations(df)
                
                # Calculate density metrics
                density_metrics = calculate_app_service_density(df)
                
                # Cost calculations disabled - requires Azure Cost Management integration
                monthly_waste = 0
                annual_savings = 0
                
                # Convert recommendations to generic dashboard format
                generic_recommendations = []
                for rec in recommendations:
                    generic_recommendations.append({
                        'type': rec.get('type', 'optimization'),
                        'resource': rec.get('resource', 'App Service Plan'),
                        'current_state': rec.get('current_state', 'Needs review'),
                        'suggestion': rec.get('suggestion', 'Review configuration'),
                        'potential_saving': rec.get('potential_saving', 'N/A'),
                        'priority': rec.get('priority', 'Medium'),
                        'impact': rec.get('impact', 'Cost optimization')
                    })
                
                # Prepare location stats in generic format
                location_stats_list = []
                for _, row in location_stats.iterrows():
                    location_stats_list.append({
                        'Location': row['Location'],
                        'Total': int(row['Plans']),
                        'Orphaned': 0,  # Will be calculated if needed
                        'Active': int(row['Plans'])
                    })
                
                # Prepare resource group stats in generic format
                rg_stats_list = []
                for _, row in rg_stats.iterrows():
                    rg_stats_list.append({
                        'ResourceGroup': row['ResourceGroup'],
                        'Total': int(row['Plans']),
                        'Orphaned': 0,  # Will be calculated if needed
                        'Active': int(row['Plans']),
                        'OrphanRate': '0%'
                    })
                
                # Prepare orphaned resources list
                orphaned_resources_list = []
                for _, plan in orphaned_plans.iterrows():
                    orphaned_resources_list.append({
                        'name': plan['NAME'],
                        'resource_group': plan['RESOURCE GROUP'],
                        'location': plan['LOCATION'],
                        'id': plan.get('ID', '')
                    })
                
                # Return data in generic dashboard format
                return jsonify({
                    'summary': {
                        'total_resources': int(total_plans),
                        'orphaned_count': len(orphaned_plans),
                        'active_count': len(active_plans),
                        'orphaned_percentage': round((len(orphaned_plans) / total_plans * 100) if total_plans > 0 else 0, 1)
                    },
                    'cost_impact': {
                        'monthly_waste': round(monthly_waste, 2),
                        'annual_savings': round(annual_savings, 2),
                        'quick_wins': [
                            {
                                'action': f'Delete {len(orphaned_plans)} orphaned App Service Plans',
                                'savings': f'${monthly_waste:.0f}/month'
                            }
                        ] if len(orphaned_plans) > 0 else []
                    },
                    'risk_assessment': {
                        'level': 'Low',
                        'items': []
                    },
                    'action_priorities': {
                        'urgent': [],
                        'high': [],
                        'low': []
                    },
                    'benchmarks': {
                        'your_orphan_rate': round((len(orphaned_plans) / total_plans * 100) if total_plans > 0 else 0, 1),
                        'avg_rg_orphan_rate': 0,
                        'best_rg': None,
                        'worst_rg': None,
                        'total_rg_count': len(rg_stats_list)
                    },
                    'recommendations': generic_recommendations,
                    'location_stats': location_stats_list,
                    'resource_group_stats': rg_stats_list,
                    'orphaned_resources': orphaned_resources_list,
                    'resource_details': [],
                    'scan_file': latest_json,
                    'scan_date': scan_data.get('timestamp', 'Unknown')
                })
                
            except Exception as e:
                return jsonify({
                    'error': 'analysis_error',
                    'message': f'Error analyzing data: {str(e)}'
                }), 500
        
        # Original CSV-based logic
        data_dir = app.config['DATA_FOLDER']
        
        # Look for all CSV files in the directory
        all_files = sorted([f for f in os.listdir(data_dir) if f.endswith('.csv')])
        
        if not all_files:
            return jsonify({
                'error': 'no_data',
                'message': 'No data files found. Please upload your CSV files to begin analysis.'
            }), 404
        
        # Determine which files to use - look for file0 (plans) and file1 (apps)
        plans_files = [f for f in all_files if '_file0_' in f]
        apps_files = [f for f in all_files if '_file1_' in f]
        
        has_plans = len(plans_files) > 0
        has_apps = len(apps_files) > 0
        
        plans_path = os.path.join(data_dir, plans_files[-1]) if has_plans else None
        apps_path = os.path.join(data_dir, apps_files[-1]) if has_apps else None
        
        # Scenario 1: Only Apps CSV (file1) uploaded
        if has_apps and not has_plans:
            data = analyze_app_services_only(apps_path)
            recommendations = generate_apps_only_recommendations(data['df'])
            
            # Create simplified charts
            plan_chart_data = {
                'labels': [item['Plan'] for item in data['plan_stats'][:10]],
                'apps': [item['Apps'] for item in data['plan_stats'][:10]]
            }
            
            location_chart_data = {
                'labels': [item['Location'] for item in data['location_stats']],
                'apps': [item['Apps'] for item in data['location_stats']]
            }
            
            tier_chart_data = {
                'labels': [item['Tier'] for item in data['tier_stats']],
                'apps': [item['Apps'] for item in data['tier_stats']]
            }
            
            combined_metadata = {
                'enabled': False,
                'files_count': 1,
                'mode': 'apps_only',
                'plans_file': None,
                'apps_file': apps_files[-1],
                'total_apps_detailed': len(data['df']),
                'running_apps': data['running_apps'],
                'stopped_apps': data['stopped_apps']
            }
            
            response_data = {
                'summary': convert_to_serializable(data['summary']),
                'recommendations': convert_to_serializable(recommendations),
                'recommendation_definitions': APP_SERVICE_RECOMMENDATIONS,
                'density_metrics': [],
                'combined_insights': combined_metadata,
                'charts': {
                    'tier': tier_chart_data,
                    'location': location_chart_data,
                    'plans': plan_chart_data,
                    'os': {
                        'labels': [item['OS'] for item in data['os_stats']],
                        'apps': [item['Apps'] for item in data['os_stats']]
                    } if data['os_stats'] else None
                },
                'tables': {
                    'tier_stats': data['tier_stats'],
                    'plan_stats': data['plan_stats'],
                    'location_stats': data['location_stats'],
                    'subscription_stats': data['subscription_stats']
                }
            }
            
            return jsonify(response_data)
        
        # Scenario 2 & 3: Plans CSV uploaded (with or without Apps CSV)
        if not has_plans:
            return jsonify({
                'error': 'missing_plans_file',
                'message': 'App Service Plans CSV (file 1) is required for full analysis. Upload it alone or with Apps CSV (file 2).'
            }), 400
        
        # Analyze plans (always required)
        data = analyze_app_service_plans(plans_path)
        df = data['df']
        
        recommendations = generate_app_service_recommendations(df)
        density_metrics = calculate_app_service_density(df)
        
        # If we have apps data, do combined analysis
        combined_insights = False
        if apps_path and os.path.exists(apps_path):
            try:
                apps_df = pd.read_csv(apps_path)
                # Add combined recommendations
                combined_recs = generate_combined_recommendations(df, apps_df)
                recommendations.extend(combined_recs)
                combined_insights = True
            except:
                pass  # Continue with just plans analysis
        
        tier_chart_data = {
            'labels': [str(item['Tier']) for item in data['tier_stats']],
            'plans': [int(item['Plans']) for item in data['tier_stats']],
            'apps': [int(item['Apps']) for item in data['tier_stats']],
            'instances': [int(item['Instances']) for item in data['tier_stats']]
        }
        
        location_chart_data = {
            'labels': [str(item['Location']) for item in data['location_stats']],
            'plans': [int(item['Plans']) for item in data['location_stats']],
            'instances': [int(item['Instances']) for item in data['location_stats']]
        }
        
        os_chart_data = {
            'labels': [str(item['OS']) for item in data['os_stats']],
            'plans': [int(item['Plans']) for item in data['os_stats']],
            'apps': [int(item['Apps']) for item in data['os_stats']]
        }
        
        # Prepare combined insights metadata
        combined_metadata = {
            'enabled': combined_insights,
            'files_count': 2 if combined_insights else 1,
            'plans_file': plans_files[-1] if plans_files else None,
            'apps_file': apps_files[-1] if apps_files else None
        }
        
        # If we have apps data, add app-specific metrics to summary
        if combined_insights and apps_path and os.path.exists(apps_path):
            try:
                apps_df = pd.read_csv(apps_path)
                combined_metadata['total_apps_detailed'] = len(apps_df)
                if 'STATUS' in apps_df.columns:
                    combined_metadata['running_apps'] = len(apps_df[apps_df['STATUS'].str.contains('Running', case=False, na=False)])
                    combined_metadata['stopped_apps'] = len(apps_df[~apps_df['STATUS'].str.contains('Running', case=False, na=False)])
            except:
                pass
        
        response_data = {
            'summary': convert_to_serializable(data['summary']),
            'recommendations': convert_to_serializable(recommendations),
            'recommendation_definitions': APP_SERVICE_RECOMMENDATIONS,
            'density_metrics': convert_to_serializable(density_metrics),
            'combined_insights': combined_metadata,
            'charts': {
                'tier': tier_chart_data,
                'location': location_chart_data,
                'os': os_chart_data
            },
            'tables': {
                'tier_stats': convert_to_serializable(data['tier_stats']),
                'location_stats': convert_to_serializable(data['location_stats']),
                'resource_groups': convert_to_serializable(data['rg_stats'])
            }
        }
        
        return jsonify(response_data)
    
    # Generic handler for all other resource types
    if resource_type in RESOURCE_TYPES:
        # Use JSON data from Azure scan
        environment_dir = app.config['ENVIRONMENT_FOLDER']
        
        # Filter files based on environment
        if is_demo_mode():
            json_files = sorted([f for f in os.listdir(environment_dir) if f.startswith(DEV_FILE_PREFIX) and f.endswith('.json')])
        else:
            json_files = sorted([f for f in os.listdir(environment_dir) 
                                if f.startswith(PROD_FILE_PREFIX) and f.endswith('.json') 
                                and not f.startswith(DEV_FILE_PREFIX)])
        
        if not json_files:
            return jsonify({
                'error': 'no_data',
                'message': 'No Azure scan data found. Please run a scan from the Overview page first.'
            }), 404
        
        # Load latest JSON scan
        latest_json = json_files[-1]
        json_path = os.path.join(environment_dir, latest_json)
        
        try:
            with open(json_path, 'r') as f:
                scan_data = json.load(f)
            
            # Map resource type to JSON key
            resource_key_mapping = {
                'sql-databases': 'sql_servers',
                'virtual-machines': 'virtual_machines',
                'public-ips': 'public_ips',
                'disks': 'disks',
                'nics': 'network_interfaces',
                'load-balancers': 'load_balancers',
                'availability-sets': 'availability_sets',
                'route-tables': 'route_tables',
                'nat-gateways': 'nat_gateways',
                'frontdoor-waf': 'frontdoor_waf_policies',
                'traffic-manager': 'traffic_manager_profiles',
                'subnets': 'subnets',
                'ip-groups': 'ip_groups',
                'private-dns': 'private_dns_zones',
                'private-endpoints': 'private_endpoints',
                'vnet-gateways': 'virtual_network_gateways',
                'ddos-plans': 'ddos_protection_plans',
                'api-connections': 'api_connections',
                'certificates': 'certificates',
                'storage-accounts': 'storage_accounts',
                'nsgs': 'network_security_groups'
            }
            
            json_key = resource_key_mapping.get(resource_type)
            if not json_key:
                return jsonify({'error': 'Invalid resource type'}), 400
            
            resources_data = scan_data.get('resources', {}).get(json_key, [])
            
            # Analyze resources
            analysis_result = analyze_generic_resource_type(resource_type, resources_data)
            
            if 'error' in analysis_result:
                return jsonify(analysis_result), 404
            
            # Add metadata
            analysis_result['data_source'] = 'azure_scan'
            analysis_result['scan_file'] = latest_json
            analysis_result['scan_date'] = scan_data.get('timestamp', 'Unknown')
            analysis_result['resource_type_name'] = RESOURCE_TYPES[resource_type]['name']
            
            return jsonify(analysis_result)
            
        except Exception as e:
            return jsonify({
                'error': 'analysis_error',
                'message': f'Error analyzing data: {str(e)}'
            }), 500
    
    return jsonify({'error': 'Invalid resource type'}), 400

@app.route('/api/export/recommendations/<resource_type>')
def export_recommendations(resource_type):
    """Export recommendations as JSON"""
    # This would be implemented similar to get_data but only return recommendations
    return jsonify({'status': 'not_implemented'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
