#!/usr/bin/env python3
"""
Debug the specific regex issues found in AI-generated patterns.
"""

import re

def test_regex_patterns():
    """Test the problematic regex patterns against real text"""
    print("🐛 DEBUGGING REGEX ISSUES")
    print("="*50)
    
    # Sample text from actual BAC email (cleaned)
    sample_text = """Hola LUIS GABRIEL GOMEZ MARTINEZ A continuación le detallamos la transacción realizada: 
    Comercio: GORDI FRUTI Ciudad y país: , Costa Rica Fecha: Jun 6, 2025, 11:45 AMEX ***********2952 
    Autorización: 208975 Referencia: Tipo de Transacción: COMPRA Monto: CRC 6,220.00"""
    
    print(f"📄 Sample text:")
    print(f"   {sample_text[:200]}...")
    
    print(f"\n🧪 TESTING CURRENT AI-GENERATED PATTERNS:")
    
    # Test current amount pattern (problematic)
    print(f"\n1. AMOUNT PATTERN (CURRENT - BROKEN):")
    amount_pattern = r'(?P<amount>CRC\s[\d{1,3}(?:,\d{3})*(?:\.\d{2})?])'
    print(f"   Pattern: {amount_pattern}")
    try:
        match = re.search(amount_pattern, sample_text)
        if match:
            print(f"   ✅ Match: '{match.group()}'")
            print(f"   Named group: '{match.groupdict().get('amount', 'None')}'")
        else:
            print(f"   ❌ No match found")
    except re.error as e:
        print(f"   ❌ REGEX ERROR: {e}")
    
    # Test corrected amount pattern
    print(f"\n2. AMOUNT PATTERN (CORRECTED):")
    corrected_amount = r'(?P<amount>CRC\s\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
    print(f"   Pattern: {corrected_amount}")
    try:
        match = re.search(corrected_amount, sample_text)
        if match:
            print(f"   ✅ Match: '{match.group()}'")
            print(f"   Named group: '{match.groupdict().get('amount', 'None')}'")
        else:
            print(f"   ❌ No match found")
    except re.error as e:
        print(f"   ❌ REGEX ERROR: {e}")
    
    # Test current description pattern (problematic)
    print(f"\n3. DESCRIPTION PATTERN (CURRENT - BROKEN):")
    desc_pattern = r'(?P<description>Comercio:\s([A-Z\s]+))'
    print(f"   Pattern: {desc_pattern}")
    try:
        match = re.search(desc_pattern, sample_text)
        if match:
            print(f"   ✅ Match: '{match.group()}'")
            print(f"   Named group: '{match.groupdict().get('description', 'None')}'")
        else:
            print(f"   ❌ No match found")
    except re.error as e:
        print(f"   ❌ REGEX ERROR: {e}")
    
    # Test corrected description pattern  
    print(f"\n4. DESCRIPTION PATTERN (CORRECTED):")
    corrected_desc = r'(?P<description>Comercio:\s+([A-Z][A-Z\s]*[A-Z]|[A-Z]+))'
    print(f"   Pattern: {corrected_desc}")
    try:
        match = re.search(corrected_desc, sample_text, re.IGNORECASE)
        if match:
            print(f"   ✅ Match: '{match.group()}'")
            print(f"   Named group: '{match.groupdict().get('description', 'None')}'")
        else:
            print(f"   ❌ No match found")
    except re.error as e:
        print(f"   ❌ REGEX ERROR: {e}")

def analyze_issues():
    """Analyze the specific issues with AI-generated regex"""
    print(f"\n🔍 ISSUE ANALYSIS:")
    print("="*50)
    
    print(f"❌ PROBLEM 1: Amount Pattern Syntax Error")
    print(f"   Current: (?P<amount>CRC\\s[\\d{{1,3}}(?:,\\d{{3}})*(?:\\.\\d{{2}})?])")
    print(f"   Issue: Square brackets around the entire digit pattern")
    print(f"   Fix: Remove the square brackets")
    print(f"   Correct: (?P<amount>CRC\\s\\d{{1,3}}(?:,\\d{{3}})*(?:\\.\\d{{2}})?)")
    
    print(f"\n❌ PROBLEM 2: Description Pattern Structure")
    print(f"   Current: (?P<description>Comercio:\\s([A-Z\\s]+))")
    print(f"   Issue: Nested parentheses create wrong capture group")
    print(f"   Fix: Use proper named group without nesting")
    print(f"   Correct: (?P<description>Comercio:\\s+([A-Z][A-Z\\s]*[A-Z]|[A-Z]+))")
    
    print(f"\n💡 ROOT CAUSE:")
    print(f"   The AI is generating syntactically valid but logically flawed regex")
    print(f"   Need to improve the prompt to be more specific about syntax")

def suggest_improvements():
    """Suggest improvements to the AI prompt"""
    print(f"\n🚀 SUGGESTED IMPROVEMENTS:")
    print("="*50)
    
    print(f"1. Add regex syntax validation in prompt")
    print(f"2. Provide specific examples of correct named groups")  
    print(f"3. Add testing instruction within the prompt")
    print(f"4. Improve the validation logic to catch syntax errors")
    print(f"5. Add regex compilation test before saving rules")

if __name__ == "__main__":
    test_regex_patterns()
    analyze_issues()
    suggest_improvements() 