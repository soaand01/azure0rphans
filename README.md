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

1. **Production Mode**: Configure Azure credentials and scan your subscription
2. **Demo Mode**: Toggle demo mode in the navigation to explore with fake data
3. **View Results**: 
   - Orphans View: See all orphaned resources
   - Complete View: Browse all resources by type
4. **Export**: Download scan results as CSV

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
