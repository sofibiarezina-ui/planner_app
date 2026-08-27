import bcrypt
import streamlit as st
from sqlalchemy.orm import Session
import crud


# хэширование ----------------------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


# интерфейс авторизации -----------------------------------------------------------------------------

def render_auth_ui(db: Session) -> bool:
    # отрисовка формы входа/регистрации в sidebar. True - пользователь авторизован, False — если нет.
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None

    # пользователь уже вошёл
    if st.session_state.user_id:
        st.sidebar.markdown(f"Пользователь: **{st.session_state.username}**")
        if st.sidebar.button("Выйти", key="logout_btn"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()
        return True

    # не авторизован -> в боковой панели
    tab_login, tab_register = st.sidebar.tabs(["Вход", "Регистрация"])

    # Форма Входа
    with tab_login:
        st.subheader("Вход")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Пароль", type="password", key="login_password")

        if st.button("Войти", key="login_btn"):
            if not email or not password:
                st.warning("Заполните все поля")
            else:
                user = crud.get_user_by_email(db, email)
                if user and verify_password(password, user.password_hash):
                    st.session_state.user_id = user.id
                    st.session_state.username = user.username
                    st.success("Успешный вход!")
                    st.rerun()
                else:
                    st.error("Неверный email или пароль")

    # Форма Регистрации
    with tab_register:
        st.subheader("Регистрация")
        username = st.text_input("Имя пользователя", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Пароль", type="password", key="reg_password")

        if st.button("Зарегистрироваться", key="reg_btn"):
            if not username or not email or not password:
                st.warning("Заполните все поля")
            elif crud.get_user_by_email(db, email):
                st.error("Пользователь с таким email уже существует")
            else:
                pwd_hash = hash_password(password)
                user = crud.create_user(db, username=username, email=email, password_hash=pwd_hash)
                st.session_state.user_id = user.id
                st.session_state.username = user.username
                st.success("Регистрация успешна!")
                st.rerun()

    return False