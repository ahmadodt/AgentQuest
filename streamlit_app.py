from src.env_loader import load_local_env
from src.app.ui_streamlit import main


if __name__ == "__main__":
    load_local_env()
    main()
