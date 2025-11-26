```
dfs
├─ client
│  ├─ file_client.py
│  ├─ gui
│  │  ├─ app.py
│  │  ├─ panels
│  │  │  ├─ left_panel.py
│  │  │  ├─ right_panel.py
│  │  │  └─ __init__.py
│  │  └─ threads.py
│  └─ handlers
│     ├─ block_table_handler.py
│     ├─ delete_handler.py
│     ├─ download_handler.py
│     ├─ info_handler.py
│     ├─ list_handler.py
│     ├─ status_handler.py
│     ├─ upload_handler.py
│     └─ __init__.py
├─ client_main.py
├─ core
│  ├─ logger.py
│  ├─ network_utils.py
│  └─ protocol.py
├─ LICENSE
├─ README.md
├─ server
│  ├─ block_table.py
│  ├─ client_handlers
│  ├─ file_server.py
│  ├─ file_table.py
│  ├─ handlers
│  │  ├─ block_table_handler.py
│  │  ├─ command_handler.py
│  │  ├─ delete_handler.py
│  │  ├─ download_handler.py
│  │  ├─ info_handler.py
│  │  ├─ list_handler.py
│  │  ├─ storage_handler.py
│  │  ├─ upload_handler.py
│  │  └─ __init__.py
│  ├─ network_server.py
│  ├─ nodes.py
│  ├─ peer_2_peer
│  └─ peer_2_peer.py
├─ server_main.py
└─ tests
   └─ verify_handlers.py

```