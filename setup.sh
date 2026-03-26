#!/bin/bash
# Setup script for Domoriks Configurator

echo "=================================="
echo "Domoriks Configurator - Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

# Run tests
echo ""
echo "Running tests..."
cd tests && python3 test_parser.py && cd ..

if [ $? -ne 0 ]; then
    echo "Warning: Some tests failed"
else
    echo "All tests passed!"
fi

# Make main.py executable
chmod +x src/main.py

echo ""
echo "=================================="
echo "Setup complete!"
echo "=================================="
echo ""
echo "To run the application:"
echo "  cd src && python3 main.py"
echo ""
echo "Or:"
echo "  ./src/main.py"
echo ""
