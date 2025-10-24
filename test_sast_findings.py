#!/usr/bin/env python3
"""
Test file for SAST findings - intentionally contains security issues
to test the PR comments functionality.
"""

import os
import subprocess
import hashlib
import base64

def insecure_password_hash(password):
    """Insecure password hashing using MD5 - should trigger SAST finding."""
    return hashlib.md5(password.encode()).hexdigest()

def hardcoded_secret():
    """Function with hardcoded secret - should trigger SAST finding."""
    api_key = "sk-1234567890abcdef1234567890abcdef"
    return api_key

def sql_injection_vulnerable(query, user_input):
    """SQL injection vulnerable code - should trigger SAST finding."""
    sql = f"SELECT * FROM users WHERE name = '{user_input}'"
    return sql

def command_injection_vulnerable(filename):
    """Command injection vulnerable code - should trigger SAST finding."""
    command = f"cat {filename}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout

def weak_random():
    """Weak random number generation - should trigger SAST finding."""
    import random
    return random.randint(1, 100)

def insecure_file_operation():
    """Insecure file operation - should trigger SAST finding."""
    with open("/tmp/sensitive_data.txt", "w") as f:
        f.write("sensitive information")
    return True

def main():
    """Main function to test SAST findings."""
    print("Testing SAST findings...")
    
    # Test insecure password hashing
    password = "password123"
    hash_result = insecure_password_hash(password)
    print(f"Password hash: {hash_result}")
    
    # Test hardcoded secret
    secret = hardcoded_secret()
    print(f"API key: {secret}")
    
    # Test SQL injection
    user_input = "admin'; DROP TABLE users; --"
    sql_query = sql_injection_vulnerable("users", user_input)
    print(f"SQL query: {sql_query}")
    
    # Test command injection
    filename = "test.txt; rm -rf /"
    command_result = command_injection_vulnerable(filename)
    print(f"Command result: {command_result}")
    
    # Test weak random
    random_num = weak_random()
    print(f"Random number: {random_num}")
    
    # Test insecure file operation
    file_result = insecure_file_operation()
    print(f"File operation result: {file_result}")

if __name__ == "__main__":
    main()
