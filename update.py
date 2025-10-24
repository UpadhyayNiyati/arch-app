# from sqlalchemy import create_engine, text
# from pymysql.err import OperationalError

# # Replace with your MySQL connection string
# # It's a good practice to load this from a config file or environment variables
# DATABASE_URL = "mysql+pymysql://root:Niya%401820@localhost/architect_mngmnt_sys"
# engine = create_engine(DATABASE_URL)


# def create_otp_table():
#     """
#     Creates the new 'otp_codes' table.
#     """
#     try:
#         with engine.connect() as connection:
#             sql_command = text("""
#                 CREATE TABLE otp_codes (
#                     id INT AUTO_INCREMENT PRIMARY KEY,
#                     user_id INT NOT NULL,
#                     otp_code VARCHAR(64) NOT NULL,
#                     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
#                     expires_at DATETIME NOT NULL,
#                     is_used BOOLEAN NOT NULL DEFAULT FALSE,
#                     attempts INT NOT NULL DEFAULT 0,
#                     type VARCHAR(50)
#                 );
#             """)
#             connection.execute(sql_command)
#             connection.commit()
#             print("Table 'otp_codes' created successfully!")
#     except OperationalError as e:
#         if "Table 'otp_codes' already exists" in str(e):
#             print("Table 'otp_codes' already exists. Skipping creation.")
#         else:
#             print(f"An unexpected error occurred while creating table: {e}")
#     except Exception as e:
#         print(f"An error occurred while creating table: {e}")
