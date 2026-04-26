# src/knowledge_graph.py
import networkx as nx
from typing import List


def create_graph():
    """
    Создает граф знаний для автоматической классификации транзакций.
    Связывает магазины с категориями расходов.
    """
    # Создаем пустой граф
    G = nx.Graph()

    # --- 1. ДОБАВЛЕНИЕ УЗЛОВ (NODES) ---
    
    # Объекты типа "А" - Магазины/Сервисы
    stores = ["Uber", "Yandex Taxi", "Starbucks", "Magnum", "McDonald's", "KFC", "Netflix"]
    G.add_nodes_from(stores, type="store")

    # Объекты типа "Б" - Категории расходов
    categories = ["Transport", "Food", "Shopping", "Entertainment", "Coffee"]
    G.add_nodes_from(categories, type="category")

    # --- 2. ДОБАВЛЕНИЕ СВЯЗЕЙ (EDGES) ---
    # Соединяем Магазины с Категориями
    # Формат: (Магазин, Категория) - Магазин относится к Категории
    relationships = [
        ("Uber", "Transport"),              # Uber относится к категории Transport
        ("Yandex Taxi", "Transport"),       # Yandex Taxi относится к категории Transport
        ("Starbucks", "Coffee"),           # Starbucks относится к категории Coffee
        ("Magnum", "Shopping"),            # Magnum относится к категории Shopping
        ("McDonald's", "Food"),            # McDonald's относится к категории Food
        ("KFC", "Food"),                   # KFC относится к категории Food
        ("Netflix", "Entertainment"),      # Netflix относится к категории Entertainment
        ("Coffee", "Food"),                # Coffee является подкатегорией Food
    ]
    G.add_edges_from(relationships)

    return G


def find_related_entities(graph, start_node):
    """
    Универсальный поиск: Найти все объекты, связанные с start_node.
    
    Args:
        graph: Граф NetworkX
        start_node: Начальный узел для поиска
        
    Returns:
        Список связанных узлов
    """
    if start_node not in graph:
        return []
    
    # Получаем соседей (все узлы, связанные с start_node)
    neighbors = list(graph.neighbors(start_node))
    return neighbors


def get_category_for_store(graph, store_name: str) -> str:
    """
    Автоматическая классификация: по названию магазина определяет категорию.
    
    Args:
        graph: Граф NetworkX
        store_name: Название магазина
        
    Returns:
        Название категории или "Other" если не найдено
    """
    if store_name not in graph:
        return "Other"
    
    # Проверяем, что это магазин
    if graph.nodes[store_name].get("type") != "store":
        return "Other"
    
    # Находим связанную категорию
    related = find_related_entities(graph, store_name)
    for node in related:
        if graph.nodes[node].get("type") == "category":
            return node
    
    return "Other"


def get_stores_in_category(graph, category_name: str) -> List[str]:
    """
    Получить все магазины в категории.
    
    Args:
        graph: Граф NetworkX
        category_name: Название категории
        
    Returns:
        Список названий магазинов
    """
    if category_name not in graph:
        return []
    
    stores = []
    related = find_related_entities(graph, category_name)
    for node in related:
        if graph.nodes[node].get("type") == "store":
            stores.append(node)
    
    return stores
