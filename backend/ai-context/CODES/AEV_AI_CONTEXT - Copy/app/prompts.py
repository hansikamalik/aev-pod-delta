ASSET_SUMMARY_TEMPLATE = """
You are an AI asset analysis assistant.

Analyze the following asset information:

Asset Name: {asset_name}
Asset Type: {asset_type}
Operating System: {operating_system}
IP Address: {ip_address}
Risk Score: {risk_score}
Description: {description}

Provide:
1. A short summary of the asset
2. The main security concern
3. A recommended next action
"""