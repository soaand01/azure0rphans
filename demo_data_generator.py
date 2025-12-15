"""
Demo Data Generator for Azure CostPlan
Generates realistic fake Azure resource data matching production structure EXACTLY
"""

import random
from datetime import datetime
import json

# Fake subscription ID (constant for consistency)
DEMO_SUBSCRIPTION_ID = "12345678-1234-1234-1234-123456789abc"

# Azure regions
AZURE_REGIONS = [
    'southafricanorth', 'eastus', 'eastus2', 'westus', 'westus2', 'centralus',
    'northeurope', 'westeurope', 'uksouth', 'ukwest',
    'southeastasia', 'eastasia', 'australiaeast',
    'brazilsouth', 'canadacentral', 'japaneast', 'francecentral'
]

# Resource groups (realistic names)
RESOURCE_GROUPS = [
    'production-rg', 'development-rg', 'networking-rg',
    'identity-server-prd', 'identity-server-dev', 'identity-server-hml',
    'app-services-rg', 'data-platform-rg', 'monitoring-rg',
    'security-rg', 'backup-rg', 'dr-rg', 'shared-services-rg',
    'web-apps-prod', 'web-apps-dev', 'databases-rg', 'storage-rg'
]

# Resource naming patterns
PREFIXES = ['prod', 'dev', 'test', 'staging', 'uat', 'dr', 'qa', 'demo', 'temp']
COMPONENTS = ['web', 'api', 'db', 'cache', 'queue', 'worker', 'app', 'svc', 'gateway', 'auth', 'frontend', 'backend']
SUFFIXES = ['001', '002', '003', '01', '02', '03', 'main', 'primary', 'secondary', 'backup', 'temp']

def generate_resource_name(resource_type):
    """Generate realistic Azure resource name"""
    prefix = random.choice(PREFIXES)
    component = random.choice(COMPONENTS)
    suffix = random.choice(SUFFIXES)
    return f"{prefix}-{component}-{resource_type}-{suffix}"

def generate_resource_id(resource_type_path, resource_group, name):
    """Generate Azure resource ID"""
    return f"/subscriptions/{DEMO_SUBSCRIPTION_ID}/resourceGroups/{resource_group}/providers/{resource_type_path}/{name}"

def generate_wasteful_environment(target_resources=1000):
    """
    Generate "Wasteful Environment" scenario matching production JSON structure
    - ~60% of resources are orphaned/wasted
    - Target: 1000 resources total (massive wasteful environment)
    - Matches EXACT production data structure
    """
    
    data = {
        'subscription_id': DEMO_SUBSCRIPTION_ID,
        'timestamp': datetime.now().isoformat(),
        'resources': {}
    }
    
    # Calculate distribution (aiming for ~1000+ resources with ALL types)
    num_disks = 150
    num_public_ips = 120
    num_nics = 180
    num_nsgs = 70
    num_route_tables = 40
    num_load_balancers = 50
    num_frontdoor_waf = 15
    num_traffic_manager = 20
    num_app_gateways = 25
    num_vnets = 50
    num_subnets = 80
    num_private_dns = 30
    num_private_endpoints = 45
    num_vnet_gateways = 20
    num_ddos_plans = 8
    num_api_connections = 35
    num_certificates = 25
    num_availability_sets = 30
    num_nat_gateways = 15
    num_app_service_plans = 55
    num_sql_servers = 35
    num_virtual_machines = 70
    num_resource_groups = len(RESOURCE_GROUPS)
    
    # === DISKS (50% orphaned) ===
    disks = []
    for i in range(num_disks):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('disk')}-{i:03d}"
        
        # 50% are orphaned
        is_orphaned = random.random() < 0.5
        
        disks.append({
            'id': generate_resource_id('Microsoft.Compute/disks', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'sku': random.choice(['Premium_LRS', 'StandardSSD_LRS', 'Standard_LRS', 'UltraSSD_LRS']),
            'size_gb': random.choice([32, 64, 128, 256, 512, 1024, 2048]),
            'disk_state': random.choice(['Unattached', 'Reserved', 'ActiveSAS']) if is_orphaned else 'Attached',
            'is_orphaned': is_orphaned
        })
    
    data['resources']['disks'] = disks
    
    # === PUBLIC IPs (60% orphaned) ===
    public_ips = []
    for i in range(num_public_ips):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('pip')}-{i:03d}"
        
        # 60% are orphaned (very wasteful!)
        is_orphaned = random.random() < 0.6
        
        public_ips.append({
            'id': generate_resource_id('Microsoft.Network/publicIPAddresses', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'sku': random.choice(['Standard', 'Basic']),
            'allocation_method': random.choice(['Static', 'Dynamic']),
            'is_orphaned': is_orphaned
        })
    
    data['resources']['public_ips'] = public_ips
    
    # === NETWORK INTERFACES (55% orphaned) ===
    network_interfaces = []
    for i in range(num_nics):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('nic')}-{i:03d}"
        
        # 55% are orphaned
        is_orphaned = random.random() < 0.55
        
        network_interfaces.append({
            'id': generate_resource_id('Microsoft.Network/networkInterfaces', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'is_orphaned': is_orphaned
        })
    
    data['resources']['network_interfaces'] = network_interfaces
    
    # === NETWORK SECURITY GROUPS ===
    network_security_groups = []
    for i in range(num_nsgs):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('nsg')}-{i:03d}"
        
        network_security_groups.append({
            'id': generate_resource_id('Microsoft.Network/networkSecurityGroups', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'security_rules_count': random.randint(0, 25)
        })
    
    data['resources']['network_security_groups'] = network_security_groups
    
    # === ROUTE TABLES ===
    route_tables = []
    for i in range(num_route_tables):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('rt')}-{i:03d}"
        
        route_tables.append({
            'id': generate_resource_id('Microsoft.Network/routeTables', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'routes_count': random.randint(0, 15),
            'disable_bgp_route_propagation': random.choice([True, False])
        })
    
    data['resources']['route_tables'] = route_tables
    
    # === LOAD BALANCERS (40% unused) ===
    load_balancers = []
    for i in range(num_load_balancers):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('lb')}-{i:03d}"
        
        # 40% have no backend pools (wasteful)
        is_unused = random.random() < 0.4
        
        load_balancers.append({
            'id': generate_resource_id('Microsoft.Network/loadBalancers', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'sku': random.choice(['Standard', 'Basic']),
            'backend_pools_count': 0 if is_unused else random.randint(1, 4),
            'rules_count': 0 if is_unused else random.randint(1, 8),
            'is_orphaned': is_unused
        })
    
    data['resources']['load_balancers'] = load_balancers
    
    # === FRONT DOOR WAF POLICIES ===
    frontdoor_waf_policies = []
    for i in range(num_frontdoor_waf):
        location = 'global'
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('waf')}-{i:03d}"
        
        frontdoor_waf_policies.append({
            'id': generate_resource_id('Microsoft.Network/FrontDoorWebApplicationFirewallPolicies', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'policy_mode': random.choice(['Prevention', 'Detection']),
            'custom_rules_count': random.randint(0, 20),
            'managed_rules_count': random.randint(1, 5)
        })
    
    data['resources']['frontdoor_waf_policies'] = frontdoor_waf_policies
    
    # === TRAFFIC MANAGER PROFILES ===
    traffic_manager_profiles = []
    for i in range(num_traffic_manager):
        location = 'global'
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('tm')}-{i:03d}"
        
        traffic_manager_profiles.append({
            'id': generate_resource_id('Microsoft.Network/trafficManagerProfiles', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'routing_method': random.choice(['Performance', 'Weighted', 'Priority', 'Geographic']),
            'endpoints_count': random.randint(1, 8),
            'status': random.choice(['Enabled', 'Disabled'])
        })
    
    data['resources']['traffic_manager_profiles'] = traffic_manager_profiles
    
    # === APPLICATION GATEWAYS ===
    application_gateways = []
    for i in range(num_app_gateways):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('agw')}-{i:03d}"
        
        application_gateways.append({
            'id': generate_resource_id('Microsoft.Network/applicationGateways', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'sku': random.choice(['Standard_v2', 'WAF_v2', 'Standard', 'WAF']),
            'capacity': random.randint(1, 10),
            'backend_pools_count': random.randint(1, 5),
            'listeners_count': random.randint(1, 10)
        })
    
    data['resources']['application_gateways'] = application_gateways
    
    # === VIRTUAL NETWORKS ===
    virtual_networks = []
    for i in range(num_vnets):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('vnet')}-{i:03d}"
        
        virtual_networks.append({
            'id': generate_resource_id('Microsoft.Network/virtualNetworks', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'address_space': [f"10.{random.randint(0, 255)}.0.0/16"],
            'subnets_count': random.randint(1, 8)
        })
    
    data['resources']['virtual_networks'] = virtual_networks
    
    # === SUBNETS ===
    subnets = []
    for i in range(num_subnets):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        vnet_name = f"vnet-{random.choice(PREFIXES)}-{random.randint(1, 20):03d}"
        name = f"subnet-{random.choice(['default', 'frontend', 'backend', 'data', 'app'])}-{i:03d}"
        
        subnets.append({
            'id': generate_resource_id('Microsoft.Network/virtualNetworks', rg, vnet_name) + f'/subnets/{name}',
            'name': name,
            'vnet_name': vnet_name,
            'resource_group': rg,
            'location': location,
            'address_prefix': f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.0/24",
            'available_ips': random.randint(50, 250)
        })
    
    data['resources']['subnets'] = subnets
    
    # === IP GROUPS (empty) ===
    data['resources']['ip_groups'] = []
    
    # === PRIVATE DNS ZONES ===
    private_dns_zones = []
    for i in range(num_private_dns):
        rg = random.choice(RESOURCE_GROUPS)
        domain = random.choice(['privatelink.database.windows.net', 'privatelink.blob.core.windows.net', 
                                'privatelink.azurewebsites.net', 'internal.company.com'])
        name = f"{domain}"
        
        private_dns_zones.append({
            'id': generate_resource_id('Microsoft.Network/privateDnsZones', rg, name),
            'name': name,
            'resource_group': rg,
            'number_of_record_sets': random.randint(1, 50),
            'number_of_virtual_network_links': random.randint(0, 5)
        })
    
    data['resources']['private_dns_zones'] = private_dns_zones
    
    # === PRIVATE ENDPOINTS ===
    private_endpoints = []
    for i in range(num_private_endpoints):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('pe')}-{i:03d}"
        
        private_endpoints.append({
            'id': generate_resource_id('Microsoft.Network/privateEndpoints', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'connection_state': random.choice(['Approved', 'Pending', 'Rejected'])
        })
    
    data['resources']['private_endpoints'] = private_endpoints
    
    # === VIRTUAL NETWORK GATEWAYS ===
    virtual_network_gateways = []
    for i in range(num_vnet_gateways):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('vgw')}-{i:03d}"
        
        virtual_network_gateways.append({
            'id': generate_resource_id('Microsoft.Network/virtualNetworkGateways', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'gateway_type': random.choice(['Vpn', 'ExpressRoute']),
            'sku': random.choice(['VpnGw1', 'VpnGw2', 'VpnGw3', 'ErGw1AZ', 'ErGw2AZ'])
        })
    
    data['resources']['virtual_network_gateways'] = virtual_network_gateways
    
    # === DDOS PROTECTION PLANS ===
    ddos_protection_plans = []
    for i in range(num_ddos_plans):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('ddos')}-{i:03d}"
        
        ddos_protection_plans.append({
            'id': generate_resource_id('Microsoft.Network/ddosProtectionPlans', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'protected_resources_count': random.randint(0, 20)
        })
    
    data['resources']['ddos_protection_plans'] = ddos_protection_plans
    
    # === API CONNECTIONS ===
    api_connections = []
    for i in range(num_api_connections):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('api')}-{i:03d}"
        
        api_connections.append({
            'id': generate_resource_id('Microsoft.Web/connections', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'api_type': random.choice(['office365', 'azureblob', 'sql', 'servicebus', 'cosmosdb']),
            'status': random.choice(['Connected', 'Error', 'Unauthenticated'])
        })
    
    data['resources']['api_connections'] = api_connections
    
    # === CERTIFICATES ===
    certificates = []
    for i in range(num_certificates):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('cert')}-{i:03d}"
        
        certificates.append({
            'id': generate_resource_id('Microsoft.Web/certificates', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'subject_name': f"*.{random.choice(['contoso', 'fabrikam', 'demo', 'app'])}.com",
            'expiration_date': f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            'issuer': random.choice(['DigiCert', 'Let\'s Encrypt', 'GlobalSign'])
        })
    
    data['resources']['certificates'] = certificates
    
    # === AVAILABILITY SETS (60% empty/wasteful) ===
    availability_sets = []
    for i in range(num_availability_sets):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('avset')}-{i:03d}"
        
        # 60% are empty (wasteful)
        is_empty = random.random() < 0.6
        
        availability_sets.append({
            'id': generate_resource_id('Microsoft.Compute/availabilitySets', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'platform_fault_domain_count': random.choice([2, 3]),
            'platform_update_domain_count': random.choice([5, 10, 20]),
            'vm_count': 0 if is_empty else random.randint(1, 5),
            'is_orphaned': is_empty
        })
    
    data['resources']['availability_sets'] = availability_sets
    
    # === NAT GATEWAYS ===
    nat_gateways = []
    for i in range(num_nat_gateways):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('nat')}-{i:03d}"
        
        nat_gateways.append({
            'id': generate_resource_id('Microsoft.Network/natGateways', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'sku': 'Standard',
            'idle_timeout_minutes': random.choice([4, 10, 15, 30]),
            'subnets_count': random.randint(0, 5)
        })
    
    data['resources']['nat_gateways'] = nat_gateways
    
    # === APP SERVICE PLANS (many oversized) ===
    app_service_plans = []
    for i in range(num_app_service_plans):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('asp')}-{i:03d}"
        
        # 70% are oversized/wasteful
        if random.random() < 0.7:
            sku = random.choice(['P1v3', 'P2v3', 'P3v3', 'P1v2', 'P2v2'])
            capacity = random.choice([3, 4, 5])
        else:
            sku = random.choice(['B1', 'B2', 'B3', 'S1', 'S2'])
            capacity = random.choice([1, 2])
        
        app_service_plans.append({
            'id': generate_resource_id('Microsoft.Web/serverfarms', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'sku': sku,
            'capacity': capacity,
            'os': random.choice(['Linux', 'Windows']),
            'number_of_sites': random.randint(1, 3) if random.random() < 0.7 else random.randint(5, 15)
        })
    
    data['resources']['app_service_plans'] = app_service_plans
    
    # === SQL SERVERS ===
    sql_servers = []
    for i in range(num_sql_servers):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('sql')}-{i:03d}".lower().replace('-', '')[:63]  # SQL server name restrictions
        
        sql_servers.append({
            'id': generate_resource_id('Microsoft.Sql/servers', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'version': random.choice(['12.0', '2.0']),
            'administrator_login': f"sqladmin{random.randint(1, 999)}",
            'databases_count': random.randint(1, 15),
            'elastic_pools_count': random.randint(0, 3)
        })
    
    data['resources']['sql_servers'] = sql_servers
    
    # === VIRTUAL MACHINES (40% stopped/deallocated) ===
    virtual_machines = []
    for i in range(num_virtual_machines):
        location = random.choice(AZURE_REGIONS)
        rg = random.choice(RESOURCE_GROUPS)
        name = f"{generate_resource_name('vm')}-{i:03d}"
        
        # 40% are stopped/deallocated (wasteful)
        is_stopped = random.random() < 0.4
        
        virtual_machines.append({
            'id': generate_resource_id('Microsoft.Compute/virtualMachines', rg, name),
            'name': name,
            'resource_group': rg,
            'location': location,
            'vm_size': random.choice(['Standard_B2s', 'Standard_B4ms', 'Standard_D2s_v3', 'Standard_D4s_v3', 
                                      'Standard_D8s_v3', 'Standard_E4s_v3', 'Standard_F4s_v2']),
            'os_type': random.choice(['Windows', 'Linux']),
            'power_state': 'VM deallocated' if is_stopped else 'VM running',
            'provisioning_state': 'Succeeded',
            'is_orphaned': is_stopped
        })
    
    data['resources']['virtual_machines'] = virtual_machines
    
    # === RESOURCE GROUPS ===
    resource_groups = []
    for rg_name in RESOURCE_GROUPS:
        resource_groups.append({
            'id': f"/subscriptions/{DEMO_SUBSCRIPTION_ID}/resourceGroups/{rg_name}",
            'name': rg_name,
            'location': random.choice(AZURE_REGIONS),
            'provisioning_state': 'Succeeded'
        })
    
    data['resources']['resource_groups'] = resource_groups
    
    return data

def save_demo_data(data, filename=None):
    """Save demo data to JSON file"""
    import os
    
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'azure_environment_{timestamp}.json'
    
    # Ensure directory exists
    os.makedirs('data/environment', exist_ok=True)
    filepath = f'data/environment/{filename}'
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath

if __name__ == '__main__':
    print("Generating wasteful environment demo data...")
    print("=" * 60)
    data = generate_wasteful_environment()
    
    total_resources = sum(len(v) for v in data['resources'].values() if isinstance(v, list))
    print(f"\nGenerated {total_resources} resources:")
    print("-" * 60)
    for resource_type, resources in data['resources'].items():
        if isinstance(resources, list) and len(resources) > 0:
            # Count orphaned if available
            orphaned = sum(1 for r in resources if r.get('is_orphaned', False))
            orphan_pct = f" ({orphaned} orphaned, {orphaned/len(resources)*100:.0f}%)" if orphaned > 0 else ""
            print(f"  {resource_type:.<40} {len(resources):>3}{orphan_pct}")
    
    filepath = save_demo_data(data)
    print("\n" + "=" * 60)
    print(f"✓ Saved to: {filepath}")
    print("=" * 60)
