# Multi-File Upload System - User Guide

## 🎯 How It Works

The platform now supports **both single and multiple CSV file uploads** depending on the analysis type.

## 📋 Upload Scenarios

### Scenario 1: Single File Upload (App Service Plans)
**When**: Analyzing just App Service Plans infrastructure

**Steps**:
1. Go to home page → Click "App Service Plans"
2. Click "Upload CSV" button
3. Select **one** CSV file (App Service Plans export)
4. Click "Upload & Analyze"

**What you get**:
- Infrastructure cost analysis
- Right-sizing recommendations
- Tier optimization

---

### Scenario 2: Multi-File Upload (Combined Analysis) ⭐ NEW!
**When**: Deep analysis combining Plans + individual Apps

**Steps**:
1. Go to home page → Click "App Services (Combined)"
2. Click "Upload CSV" button
3. You'll see **TWO file upload fields**:
   - **File 1**: App Service Plans CSV
   - **File 2**: App Services CSV
4. Select both files
5. Click "Upload & Analyze"

**What you get**:
- Everything from single analysis PLUS:
- App-to-plan mapping
- Unused app detection
- Per-app cost attribution
- Better consolidation recommendations

---

## 📊 Azure Export Instructions

### Export App Service Plans
1. Azure Portal → App Service Plans
2. Select all plans
3. Export → CSV
4. Save as `appServicePlans.csv`

### Export App Services
1. Azure Portal → App Services
2. Select all services
3. Export → CSV
4. Save as `appServices.csv`

---

## 🎨 UI Features

### Single File Upload Modal
```
┌─────────────────────────────────┐
│ Upload CSV File                 │
├─────────────────────────────────┤
│ ℹ Upload a CSV file containing │
│   App Service Plans data...     │
│                                 │
│ [Select CSV File] [Browse...]  │
│                                 │
│ [Cancel]  [Upload & Analyze]   │
└─────────────────────────────────┘
```

### Multi-File Upload Modal
```
┌─────────────────────────────────┐
│ Upload CSV Files                │
├─────────────────────────────────┤
│ ℹ This requires MULTIPLE files │
│                                 │
│ 1. App Service Plans CSV        │
│ [Select file] [Browse...]       │
│ Required CSV file 1 of 2        │
│                                 │
│ 2. App Services CSV             │
│ [Select file] [Browse...]       │
│ Required CSV file 2 of 2        │
│                                 │
│ [Cancel]  [Upload & Analyze]   │
└─────────────────────────────────┘
```

---

## 🔧 Technical Details

### File Storage
- Uploaded files: `data/uploads/`
- Naming: `{resource-type}_file{N}_{timestamp}_{original-name}.csv`
- Example: `app-service-combined_file0_20251204_153045_plans.csv`

### Resource Types Configuration
```python
'app-service': {
    'requires_multiple': False,  # Single file
    'file_labels': None
}

'app-service-combined': {
    'requires_multiple': True,   # Multiple files
    'file_labels': [
        'App Service Plans CSV',
        'App Services CSV'
    ]
}
```

---

## 💡 Benefits of Combined Analysis

| Feature | Plans Only | Combined |
|---------|-----------|----------|
| Infrastructure costs | ✅ | ✅ |
| Right-sizing | ✅ | ✅ |
| Unused apps detection | ❌ | ✅ |
| App-level cost | ❌ | ✅ |
| Runtime insights | ❌ | ✅ |
| Stopped resources | ❌ | ✅ |
| Consolidation mapping | Basic | Advanced |

---

## 🚀 Future Extensions

This system supports adding more multi-file scenarios:

- **VMs + Disks**: Combined VM and disk analysis
- **Storage + Blobs**: Account + container level analysis
- **Network + Endpoints**: Network topology + endpoint costs

Simply add to `RESOURCE_TYPES` with `requires_multiple: True`!
