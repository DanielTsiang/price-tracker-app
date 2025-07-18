import streamlit.web.cli as stcli

if __name__ == "__main__":
    # The target script to run
    target_script = "app.py"

    # This is the command that will be executed, equivalent to:
    # streamlit run app.py
    args = ["run", target_script]

    stcli.main(args)
