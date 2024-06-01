"""
 @file database.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief initializes the database
 @version 1.0.0
 @date 2024-06-01
 
 This program intializes the database
 
"""
import sqlite3
import click
from flask import current_app, g
def get_database():
    if "database" not in g:
        g.database=sqlite3.connect(
            current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES    
        )
        g.database.row_factory = sqlite3.Row
    return g.database
def close_database(e=None):
    database=g.pop("database",None)
    if database is not None:
        database.close()
def init_database():
    database=get_database
    with current_app.open_resource("schema.sql") as schema:
        database.executescript(schema.read().decode("utf8"))
@click.command("init-database")
def init_database_command():
    init_database()
    click.echo("initialized the database")
def init_app(application):
    application.teardown_appcontext(close_database)
    application.cli.add_command(init_database_command)
    