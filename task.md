1. Create a new VPC, or use the default VPC.
    If creating a new VPC, select ‘VPC and more’ and the default settings when creating it.
2. Create the RDS instance.
    Select PostgreSQL. Make sure you enable ‘Public access’ and select ’Create new VPC security group’.

3. Change inbound rule on the newly created VPC security group to 0.0.0.0/0.

4. Connect using ’psql postgresql://username:password@host:port’
5. create .env file
copy variables from .env.example, fill the values