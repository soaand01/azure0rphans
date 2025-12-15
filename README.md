# CostPlan

Azure resource optimization platform for identifying orphaned resources and cost-saving opportunities.

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)

## 🎯 Features

- **Environment Scanning**: Scan Azure subscriptions for orphaned resources
- **Demo Mode**: Generate realistic fake data for demonstrations
- **Orphaned Resources Detection**: Identify unattached disks, public IPs, NICs, load balancers, stopped VMs, and more
- **Complete View**: Browse all Azure resources across 23+ resource types
- **Export**: Download scan results and orphaned resources as CSV

## 🚀 Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**
   ```bash
   python3 app.py
   ```

3. **Access at** `http://localhost:5000`

## 📋 Usage

### Production Mode (Azure Authentication Required)

To scan your actual Azure subscription:

1. **Authenticate with Azure CLI**
   ```bash
   az login
   ```

2. **Select your subscription**
   ```bash
   az account set --subscription "your-subscription-id-or-name"
   ```

3. **Start the application** and scan your environment

### Demo Mode

Toggle demo mode in the navigation to explore with fake data (no Azure authentication needed).

### View Results

- **Orphans View**: See all orphaned resources
- **Complete View**: Browse all resources by type
- **Export**: Download scan results as CSV

## 🔧 Supported Resources

Detects orphaned resources across 23+ Azure resource types:
- Disks, Public IPs, Network Interfaces
- Load Balancers, Availability Sets
- Virtual Machines (stopped/deallocated)
- Network Security Groups, VNets, Subnets
- NAT Gateways, Application Gateways
- SQL Servers, App Service Plans
- And more...

## 🛠️ Technologies

- Python 3 + Flask
- Azure SDK for Python
- Bootstrap 5 + Chart.js
- Pandas for data processing

---

**Built for Azure Resource Optimization**
