import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QWidget, QComboBox, QLabel,
    QVBoxLayout, QPushButton, QMessageBox, QLineEdit, QTextEdit, QGroupBox, QHBoxLayout
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class ThemeManager:
    current_theme = "Светлая тема"

    @classmethod
    def set_theme(cls, theme):
        cls.current_theme = theme

    @classmethod
    def apply_theme(cls, widget):
        if cls.current_theme == "Светлая тема":
            widget.setStyleSheet("background-color: #ffffff; color: #000000;")
        else:
            widget.setStyleSheet("background-color: #333333; color: #ffffff;")


class Database:
    def __init__(self, db_name='sneakers.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                total_price REAL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                brand TEXT,
                model TEXT,
                size TEXT,
                price REAL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        self.conn.commit()

    def register_user(self, username, password):
        try:
            self.cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return False

    def authenticate_user(self, username, password):
        self.cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        return self.cursor.fetchone()

    def get_cart_items(self, user_id):
        self.cursor.execute('SELECT brand, model, size, price FROM cart WHERE user_id=?', (user_id,))
        return self.cursor.fetchall()

    def add_to_cart(self, user_id, brand, model, size, price):
        self.cursor.execute('INSERT INTO cart (user_id, brand, model, size, price) VALUES (?, ?, ?, ?, ?)',
                            (user_id, brand, model, size, price))
        self.conn.commit()

    def clear_cart(self, user_id):
        self.cursor.execute('DELETE FROM cart WHERE user_id=?', (user_id,))
        self.conn.commit()

    def create_order(self, user_id, total_price):
        self.cursor.execute('''
            INSERT INTO orders (user_id, total_price)
            VALUES (?, ?)
        ''', (user_id, total_price))
        self.conn.commit()

    def get_all_brands(self):
        self.cursor.execute('SELECT DISTINCT brand FROM sneakers')
        return [brand[0] for brand in self.cursor.fetchall()]

    def get_models_by_brand(self, brand):
        self.cursor.execute('SELECT model FROM sneakers WHERE brand = ?', (brand,))
        return [model[0] for model in self.cursor.fetchall()]

    def get_price(self, brand, model):
        self.cursor.execute('SELECT price FROM sneakers WHERE brand = ? AND model = ?', (brand, model))
        price = self.cursor.fetchone()
        return price[0] if price else None

    def get_user_orders(self, user_id):
        self.cursor.execute('SELECT id, total_price FROM orders WHERE user_id=?', (user_id,))
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()


class BaseWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.themeComboBox = QComboBox()
        self.themeComboBox.addItem("Светлая тема")
        self.themeComboBox.addItem("Темная тема")
        self.themeComboBox.currentIndexChanged.connect(self.changeTheme)
        self.setFont(QFont("Arial", 10))

    def changeTheme(self):
        selected_theme = self.themeComboBox.currentText()
        ThemeManager.set_theme(selected_theme)
        ThemeManager.apply_theme(self)

        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, BaseWindow):
                ThemeManager.apply_theme(widget)


class SneakerBrowser(BaseWindow):
    def __init__(self, user_id):
        super().__init__()
        self.db = Database()
        self.user_id = user_id
        self.initUI()
        self.models = {}
        self.cart = []
        self.load_cart()

    def initUI(self):
        self.setWindowTitle("Sneaker Browser")
        self.setGeometry(300, 300, 400, 400)

        layout = QVBoxLayout()
        layout.addWidget(self.themeComboBox)

        brand_model_group = QGroupBox("Выбор кроссовок")
        brand_model_group.setFont(QFont("Arial", 12))
        brand_model_layout = QVBoxLayout()

        self.brandComboBox = QComboBox()
        self.brandComboBox.addItem("Выберите бренд")
        self.loadBrands()
        self.brandComboBox.currentTextChanged.connect(self.onBrandChanged)
        brand_model_layout.addWidget(QLabel("Бренд:"))
        brand_model_layout.addWidget(self.brandComboBox)

        self.modelComboBox = QComboBox()
        self.modelComboBox.addItem("Выберите модель")
        brand_model_layout.addWidget(QLabel("Модель:"))
        brand_model_layout.addWidget(self.modelComboBox)

        self.sizeComboBox = QComboBox()
        self.sizeComboBox.addItem("Выберите размер")
        self.loadSizes()
        brand_model_layout.addWidget(QLabel("Размер:"))
        brand_model_layout.addWidget(self.sizeComboBox)

        brand_model_group.setLayout(brand_model_layout)
        layout.addWidget(brand_model_group)

        button_layout = QHBoxLayout()
        self.addToCartButton = QPushButton("Добавить в корзину")
        self.addToCartButton.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px;")
        self.addToCartButton.clicked.connect(self.addToCart)
        button_layout.addWidget(self.addToCartButton)

        self.checkoutButton = QPushButton("Перейти к оплате")
        self.checkoutButton.setStyleSheet("background-color: #2196F3; color: white; font-size: 14px;")
        self.checkoutButton.clicked.connect(self.openPaymentWindow)
        button_layout.addWidget(self.checkoutButton)

        self.profileButton = QPushButton("Профиль")
        self.profileButton.setStyleSheet("background-color: #FF9800; color: white; font-size: 14px;")
        self.profileButton.clicked.connect(self.openProfileWindow)
        button_layout.addWidget(self.profileButton)

        layout.addLayout(button_layout)

        self.resultLabel = QLabel()
        layout.addWidget(self.resultLabel)

        self.cartLabel = QLabel("Корзина: Пусто")
        layout.addWidget(self.cartLabel)

        self.totalPriceLabel = QLabel("Общая стоимость: \\\\$0.00")
        layout.addWidget(self.totalPriceLabel)

        self.setLayout(layout)
        ThemeManager.apply_theme(self)

    def loadBrands(self):
        brands = self.db.get_all_brands()
        for brand in brands:
            self.brandComboBox.addItem(brand)

    def onBrandChanged(self, brand):
        self.modelComboBox.clear()
        self.modelComboBox.addItem("Выберите модель")
        self.models[brand] = self.db.get_models_by_brand(brand)
        if brand in self.models:
            self.modelComboBox.addItems(self.models[brand])
        self.modelComboBox.currentTextChanged.connect(self.onModelChanged)

    def onModelChanged(self, model):
        brand = self.brandComboBox.currentText()
        if brand != "Выберите бренд" and model != "Выберите модель":
            self.resultLabel.setText(f"{brand} {model} найдено!")
        else:
            self.resultLabel.setText("Модель не найдена!")

    def loadSizes(self):
        for size in range(36, 47):
            self.sizeComboBox.addItem(str(size))

    def addToCart(self):
        brand = self.brandComboBox.currentText()
        model = self.modelComboBox.currentText()
        size = self.sizeComboBox.currentText()
        if brand != "Выберите бренд" and model != "Выберите модель" and size != "Выберите размер":
            price = self.db.get_price(brand, model)
            if price is not None:
                self.db.add_to_cart(self.user_id, brand, model, size, price)
                self.cart.append((brand, model, size, price))
                QMessageBox.information(self, "Добавлено в корзину",
                                        f"{model} размер {size} добавлено в корзину по цене ${price:.2f}")
                self.updateCartDisplay()
            else:
                QMessageBox.warning(self, "Ошибка", "Цена не найдена.")
        else:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите бренд, модель и размер.")

    def load_cart(self):
        self.cart = self.db.get_cart_items(self.user_id)
        self.updateCartDisplay()

    def updateCartDisplay(self):
        if not self.cart:
            self.cartLabel.setText("Корзина: Пусто")
            self.totalPriceLabel.setText("Общая стоимость: \\\\$0.00")
            return
        cart_items = "\n".join(
            [f"{brand} {model} размер {size} - ${price:.2f}" for brand, model, size, price in self.cart])
        total_price = sum(price for _, _, _, price in self.cart)
        self.cartLabel.setText(f"Корзина:\n{cart_items}")
        self.totalPriceLabel.setText(f"Общая стоимость: ${total_price:.2f}")

    def openPaymentWindow(self):
        if not self.cart:
            QMessageBox.warning(self, "Ошибка", "Корзина пуста. Добавьте товары для оформления заказа.")
            return
        total_price = sum(price for _, _, _, price in self.cart)
        self.payment_window = PaymentWindow(self.user_id, total_price)
        ThemeManager.apply_theme(self.payment_window)
        self.payment_window.show()

    def openProfileWindow(self):
        self.profile_window = ProfileWindow(self.user_id)
        ThemeManager.apply_theme(self.profile_window)
        self.profile_window.show()


class ProfileWindow(BaseWindow):
    def __init__(self, user_id):
        super().__init__()
        self.db = Database()
        self.user_id = user_id
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Профиль пользователя")
        self.setGeometry(300, 300, 400, 300)

        layout = QVBoxLayout()
        layout.addWidget(self.themeComboBox)

        self.orderHistoryText = QTextEdit(self)
        self.orderHistoryText.setReadOnly(True)
        layout.addWidget(QLabel("История заказов:"))
        layout.addWidget(self.orderHistoryText)

        self.loadOrderHistory()

        self.setLayout(layout)
        ThemeManager.apply_theme(self)

    def loadOrderHistory(self):
        orders = self.db.get_user_orders(self.user_id)
        if not orders:
            self.orderHistoryText.setPlainText("История заказов пуста.")
            return
        order_details = "\n".join([f"Заказ ID: {order[0]}, Общая стоимость: ${order[1]:.2f}" for order in orders])
        self.orderHistoryText.setPlainText(order_details)


class PaymentWindow(BaseWindow):
    def __init__(self, user_id, total_price):
        super().__init__()
        self.user_id = user_id
        self.total_price = total_price
        self.db = Database()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Оплата")
        self.setGeometry(300, 300, 300, 200)

        layout = QVBoxLayout()
        layout.addWidget(self.themeComboBox)

        payment_group = QGroupBox("Детали оплаты")
        payment_group.setFont(QFont("Arial", 12))
        payment_layout = QVBoxLayout()

        self.card_number_input = QLineEdit(self)
        self.card_number_input.setPlaceholderText("Номер карты (XXXX-XXXX-XXXX-XXXX)")
        payment_layout.addWidget(self.card_number_input)

        self.expiry_date_input = QLineEdit(self)
        self.expiry_date_input.setPlaceholderText("Срок действия (MM/YY)")
        payment_layout.addWidget(self.expiry_date_input)

        self.cvc_input = QLineEdit(self)
        self.cvc_input.setPlaceholderText("CVC")
        payment_layout.addWidget(self.cvc_input)

        payment_group.setLayout(payment_layout)
        layout.addWidget(payment_group)

        self.pay_button = QPushButton("Оплатить", self)
        self.pay_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px;")
        self.pay_button.clicked.connect(self.processPayment)
        layout.addWidget(self.pay_button)

        self.setLayout(layout)
        ThemeManager.apply_theme(self)

    def processPayment(self):
        card_number = self.card_number_input.text().strip()
        expiry_date = self.expiry_date_input.text().strip()
        cvc = self.cvc_input.text().strip()

        if not card_number or not expiry_date or not cvc:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, заполните все поля.")
            return

        try:
            self.completeOrder()
            self.db.clear_cart(self.user_id)
            QMessageBox.information(self, "Успех", f"Покупка отправлена!\nЗаказ будет доставлен ровно через неделю!")
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при обработке платежа: {str(e)}")

    def completeOrder(self):
        self.db.create_order(self.user_id, self.total_price)


class RegistrationWindow(BaseWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Регистрация")
        self.setGeometry(300, 300, 300, 200)

        layout = QVBoxLayout()
        layout.addWidget(self.themeComboBox)

        registration_group = QGroupBox("Регистрация")
        registration_group.setFont(QFont("Arial", 12))
        registration_layout = QVBoxLayout()

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Имя пользователя")
        registration_layout.addWidget(self.username_input)

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        registration_layout.addWidget(self.password_input)

        self.register_button = QPushButton("Зарегистрироваться", self)
        self.register_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px;")
        self.register_button.clicked.connect(self.register)
        registration_layout.addWidget(self.register_button)

        self.login_button = QPushButton("Уже зарегистрированы? Войти", self)
        self.login_button.clicked.connect(self.openLoginWindow)
        registration_layout.addWidget(self.login_button)

        registration_group.setLayout(registration_layout)
        layout.addWidget(registration_group)

        self.setLayout(layout)
        ThemeManager.apply_theme(self)

    def register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Имя пользователя и пароль не могут быть пустыми.")
            return

        if self.db.register_user(username, password):
            QMessageBox.information(self, "Успех", "Пользователь зарегистрирован!")
            self.openSneakerBrowser()
            self.close()
        else:
            QMessageBox.warning(self, "Ошибка", "Пользователь с таким именем уже существует.")

    def openSneakerBrowser(self, user_id=None):
        self.sneaker_browser = SneakerBrowser(user_id)
        ThemeManager.apply_theme(self.sneaker_browser)
        self.sneaker_browser.show()

    def openLoginWindow(self):
        self.login_window = LoginWindow(self.db)
        ThemeManager.apply_theme(self.login_window)
        self.login_window.show()
        self.close()


class LoginWindow(BaseWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Вход")
        self.setGeometry(300, 300, 300, 200)

        layout = QVBoxLayout()
        layout.addWidget(self.themeComboBox)

        login_group = QGroupBox("Вход")
        login_group.setFont(QFont("Arial", 12))
        login_layout = QVBoxLayout()

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Имя пользователя")
        login_layout.addWidget(self.username_input)

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        login_layout.addWidget(self.password_input)

        self.login_button = QPushButton("Войти", self)
        self.login_button.setStyleSheet("background-color: #2196F3; color: white; font-size: 14px;")
        self.login_button.clicked.connect(self.login)
        login_layout.addWidget(self.login_button)

        login_group.setLayout(login_layout)
        layout.addWidget(login_group)

        self.setLayout(layout)
        ThemeManager.apply_theme(self)

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        user = self.db.authenticate_user(username, password)
        if user:
            user_id = user[0]
            QMessageBox.information(self, "Успех", "Вы успешно вошли в систему!")
            self.openSneakerBrowser(user_id)
            self.close()
        else:
            QMessageBox.warning(self, "Ошибка", "Неправильное имя пользователя или пароль.")

    def openSneakerBrowser(self, user_id):
        self.sneaker_browser = SneakerBrowser(user_id)
        ThemeManager.apply_theme(self.sneaker_browser)
        self.sneaker_browser.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    db = Database()
    registration_window = RegistrationWindow(db)
    registration_window.show()
    sys.exit(app.exec())
