#!/bin/bash

# Rosetta Frontend - Quick Start Script

echo "🚀 Rosetta Frontend Setup"
echo "=========================="
echo ""

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js version: $(node -v)"
echo ""

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    echo "⚠️  pnpm not found. Installing pnpm..."
    npm install -g pnpm
fi

echo "✅ pnpm version: $(pnpm -v)"
echo ""

# Navigate to frontend directory
cd "$(dirname "$0")"
echo "📂 Current directory: $(pwd)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pnpm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "✅ Dependencies installed successfully!"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# API Configuration
API_BASE_URL=http://localhost:8000/api

# Nuxt Configuration
NUXT_PUBLIC_API_BASE=http://localhost:8000/api
EOF
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Make sure backend is running: http://localhost:8000"
echo "   2. Start dev server: pnpm dev"
echo "   3. Visit OOBE: http://localhost:3000/oobe"
echo "   4. Complete installation wizard"
echo ""
echo "🚀 Starting development server..."
echo ""

pnpm dev
