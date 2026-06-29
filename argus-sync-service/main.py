from connectors.sql_server import SQLServerConnector


def main():
    print("ARGUS Sync Service started")

    sql_connector = SQLServerConnector()
    sql_connector.show_config()


if __name__ == "__main__":
    main()