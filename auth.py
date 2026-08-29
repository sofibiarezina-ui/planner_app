import bcrypt
import streamlit as st
import extra_streamlit_components as stx
from sqlalchemy.orm import Session
import crud
from datetime import datetime, timedelta


#@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager(key="auth_cookies")


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def render_auth_ui(db: Session) -> bool:
    cm = get_cookie_manager()

    if "user_id" not in st.session_state:
        st.session_state.user_id = None
        st.session_state.username = None

    # Автоматический вход по Cookie
    auth_token = cm.get(cookie="auth_token")
    if not st.session_state.user_id and auth_token:
        user = crud.get_user_by_session_token(db, auth_token)
        if user:
            st.session_state.user_id = user.id
            st.session_state.username = user.username

    # Если авторизован
    if st.session_state.user_id:
        st.sidebar.markdown(f"User: **{st.session_state.username}**")
        if st.sidebar.button("Log out", key="logout_btn"):
            crud.logout_user_session(db, st.session_state.user_id)
            cm.delete("auth_token")
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()
        return True

    # Формы входа / регистрации
    tab_login, tab_register = st.sidebar.tabs(["Log in", "Sign in"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Log in", key="login_btn"):
            user = crud.get_user_by_email(db, email)
            if user and verify_password(password, user.password_hash):
                st.session_state.user_id = user.id
                st.session_state.username = user.username
                token = crud.create_user_session(db, user.id)
                cm.set("auth_token", token, expires_at=datetime.utcnow() + timedelta(days=14))
                st.success("Success!")
                st.rerun()
            else:
                st.error("Incorrect email or password")

    with tab_register:
        username = st.text_input("User's name", key="reg_username")
        email_reg = st.text_input("Email", key="reg_email")
        password_reg = st.text_input("Password", type="password", key="reg_password")
        if st.button("Sign in", key="reg_btn"):
            if crud.get_user_by_email(db, email_reg):
                st.error("User with such email already exists")
            elif username and email_reg and password_reg:
                user = crud.create_user(db, username=username, email=email_reg,
                                        password_hash=hash_password(password_reg))
                st.session_state.user_id = user.id
                st.session_state.username = user.username
                token = crud.create_user_session(db, user.id)
                cm.set("auth_token", token, expires_at=datetime.utcnow() + timedelta(days=14))
                st.success("Success!")
                st.rerun()
    return False