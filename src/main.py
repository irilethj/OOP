from __future__ import annotations
import datetime
from enum import Enum
from abc import ABC, abstractmethod


class Product:
    def __init__(self, product_id: int, name: str, price: float, quantity: int):
        self.id = product_id
        self.name = name
        self.price = price
        self._quantity = quantity
        self.__secret_code = f"PRD{self.id}"

    def reduce_stock(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("The quantity must be positive.")
        if amount > self._quantity:
            raise ValueError(
                f"Not enough goods {self.name}. Available {self._quantity}. Requested {amount}"
            )
        self._quantity -= amount

    def increase_stock(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("The quantity must be positive.")
        self._quantity += amount

    def is_available(self, quantity: int = 1) -> bool:
        return self._quantity >= quantity

    @property
    def quantity(self) -> int:
        return self._quantity

    def __str__(self) -> str:
        return f"{self.name} - {self.price}$. Remaining {self.quantity}"

    def __repr__(self) -> str:
        return f"Product(product_id={self.id}, name={self.name}, price={self.price}, quantity={self.quantity})"


class OrderItem:
    def __init__(self, product: Product, quantity: int):
        if not product.is_available(quantity):
            raise ValueError(f"Product {product.name} not available in quantity {quantity}")
        self.product = product
        self.quantity = quantity
        product.reduce_stock(quantity)

    @property
    def total_cost(self) -> float:
        return self.product.price * self.quantity

    def __repr__(self) -> str:
        return f"OrderItem(product={self.product}, quantity={self.quantity})"


class OrderStatus(Enum):
    CREATED = "created"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order:
    def __init__(self, order_id: int, customer: "Customer" | None = None):
        self.order_id: int = order_id
        self.customer = customer
        self.status = OrderStatus.CREATED
        self.created_date = datetime.datetime.now()
        self._items: dict[int, OrderItem] = {}
        # КОМПОЗИЦИЯ: Order "владеет" OrderItem'ами - они создаются и уничтожаются вместе с Order

    def add_item(self, product: Product, quantity: int) -> None:
        if self.status != OrderStatus.CREATED:
            raise ValueError("Paid or processed orders cannot be changed.")

        if not product.is_available(quantity):
            raise ValueError(f"Not enough goods '{product.name}'")

        if product.id in self._items:
            product.reduce_stock(quantity)
            self._items[product.id].quantity += quantity
        else:
            self._items[product.id] = OrderItem(product, quantity)

    def remove_item(self, product_id: int) -> None:
        if self.status != OrderStatus.CREATED:
            raise ValueError("Paid or processed orders cannot be changed.")

        if product_id not in self._items:
            raise ValueError(f"Product with ID {product_id} not found in order")

        self._items[product_id].product.increase_stock(self._items[product_id].quantity)
        del self._items[product_id]

    @property
    def total_cost(self) -> float:
        return sum([order_item.total_cost for order_item in self._items.values()])

    def pay(self) -> None:
        if self.status != OrderStatus.CREATED:
            raise ValueError("The order has already been paid or canceled.")
        if not self._items:
            raise ValueError("Cannot pay for an empty order.")
        self.status = OrderStatus.PAID

    def cancel(self) -> None:
        if self.status not in [OrderStatus.CREATED, OrderStatus.PAID]:
            raise ValueError("Cannot cancel a delivered order.")

        for item in self._items.values():
            item.product.increase_stock(item.quantity)
        self.status = OrderStatus.CANCELLED

    def __len__(self) -> int:
        return len(self._items)

    def __str__(self) -> str:
        items_str = "\n".join(f"  - {item}" for item in self._items.values())
        return f"Order #{self.order_id} ({self.status})\n{items_str}\nTotal: {self.total_cost}$"

    def __repr__(self) -> str:
        return f"Order(order_id={self.order_id}, customer={self.customer})"


class User(ABC):
    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self._password = "default_password"

    def authenticate(self, password: str) -> bool:
        return self._password == password

    @property
    @abstractmethod
    def info(self) -> str:
        pass

    def __str__(self) -> str:
        return self.info


class Customer(User):
    def __init__(self, user_id: int, name: str, email: str, address: str):
        super().__init__(user_id, name, email)
        self.address = address
        self._order_history: list[Order] = []

    @property
    def order_history(self) -> list:
        return self._order_history

    def create_order(self) -> Order:
        return Order(len(self.order_history) + 1, self)

    def add_to_history(self, order: Order) -> None:
        if order not in self.order_history:
            self._order_history.append(order)

    @property
    def info(self) -> str:
        return f"Customer: {self.name} ({self.email}) orders: {len(self.order_history)}"

    @property
    def total_spent(self) -> float:
        return sum(
            order.total_cost
            for order in self.order_history
            if order.status != OrderStatus.CANCELLED
        )


class Admin(User):
    def __init__(self, user_id: int, name: str, email: str, access_level: str = "moderator"):
        super().__init__(user_id, name, email)
        self.access_level = access_level

    def add_product(
        self, products: list, product_id: int, name: str, price: float, quantity: int
    ) -> Product:
        product = Product(product_id, name, price, quantity)
        products.append(product)
        return product

    def view_all_orders(self, customers: list) -> list:
        all_orders = []
        for customer in customers:
            all_orders.extend(customer.order_history())
        return all_orders

    @property
    def info(self) -> str:
        return f"Admin: {self.name} ({self.email}) (Access level: {self.access_level})"


class Currency(Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentField(Enum):
    CARD_NUMBER = "card_number"
    EXPIRY_DATE = "expiry_date"
    CVV = "cvv"


class PaymentProcessor:
    def __init__(self) -> None:
        self._supported_currencies = list(Currency)

    def is_currency_supported(self, currency: Currency) -> bool:
        return currency in self._supported_currencies

    def process_payment(self, order: Order, payment_details: dict) -> bool:
        if order.total_cost <= 0:
            raise ValueError("The order amount must be positive.")

        if not self._validate_payment_details(payment_details):
            return False

        order.pay()
        return True

    def _validate_payment_details(self, payment_details: dict) -> bool:
        return all(field in payment_details for field in PaymentField)


class ShippingService:
    def __init__(self) -> None:
        self.tracking_numbers: dict[int, str] = {}

    def schedule_shipping(self, order: Order, address: str) -> str:
        if order.status != OrderStatus.PAID:
            raise ValueError("Only paid orders can be shipped.")

        tracking_number = f"TRK{order.order_id:06d}"
        self.tracking_numbers[order.order_id] = tracking_number

        order.status = OrderStatus.SHIPPED
        return tracking_number

    def deliver_order(self, order: Order) -> None:
        if order.status != OrderStatus.SHIPPED:
            raise ValueError("Order has not yet been shipped")

        order.status = OrderStatus.DELIVERED
