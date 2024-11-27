from sqlalchemy import text

from db import engine

sql_query = "SELECT ProductName FROM Products"

# Execute SQL query
with engine.connect() as connection:
    result = connection.execute(text(sql_query))
    rows = [dict(row._mapping) for row in result]

# File to save formatted product names
output_file = "train.txt"


# Function to format and save product names
def save_products_to_txt(products, file_path):
    with open(file_path, "w", encoding="utf-8") as file:
        for product in products:
            product_name = product.get("ProductName", "")
            # Split product name into words and write each word on a new line
            file.write("\n".join(product_name.split()))
            # Add a blank line to separate products
            file.write("\n\n")
    print(f"Product names saved to {file_path}")


# Run the function
save_products_to_txt(rows, output_file)
