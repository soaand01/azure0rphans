#!/bin/bash

echo "🚀 Starting 0rphans Setup..."
echo ""

# Check Python version
echo "✓ Checking Python version..."
python3 --version

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the dashboard, run:"
echo "  python3 app.py"
echo ""
echo "Then open your browser to: http://localhost:5000"
echo ""
