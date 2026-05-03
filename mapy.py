import tkinter as tk
from tkinter import messagebox
import requests
import json
import os

# ========================================
# КОНСТАНТЫ И НАСТРОЙКИ
# ========================================
# Имя файла для сохранения избранных пользователей
FAVORITES_FILE = 'favorites.json'

# GitHub API базовый URL для поиска пользователей
GITHUB_SEARCH_API = 'https://api.github.com/search/users'

# Максимальное количество результатов поиска для отображения
MAX_RESULTS = 15


class GitHubFinderApp:
    """
    GUI приложение для поиска пользователей GitHub и управления избранным.
    Использует официальный GitHub Search API v3.
    """

    def __init__(self, root):
        """
        Инициализация приложения.
        Создает окно, загружает избранное и настраивает интерфейс.
        """
        # Основное окно приложения
        self.root = root
        self.root.title("🔍 GitHub User Finder v2.0")
        self.root.geometry("500x650")
        self.root.resizable(True, True)

        # Загрузка избранных пользователей из файла
        self.favorites = self.load_favorites()
        self.selected_result_index = None  # Индекс выбранного результата поиска

        self.setup_ui()
        self.update_fav_listbox()  # Обновляем список избранного при запуске

    def setup_ui(self):
        """
        Создание и настройка всех элементов пользовательского интерфейса.
        """
        # ========================================
        # 1. ЗАГОЛОВОК ПРИЛОЖЕНИЯ
        # ========================================
        title_label = tk.Label(
            self.root,
            text="🔍 GitHub User Finder",
            font=("Arial", 16, "bold"),
            fg="#2d5aa0"
        )
        title_label.pack(pady=(20, 10))

        # ========================================
        # 2. ПОЛЕ ПОИСКА
        # ========================================
        search_frame = tk.Frame(self.root)
        search_frame.pack(pady=10, padx=20, fill=tk.X)

        tk.Label(
            search_frame,
            text="👤 Введите имя/логин для поиска:",
            font=("Arial", 10)
        ).pack(anchor=tk.W)

        # Переменная для хранения текста поиска
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=50,
            font=("Arial", 11),
            relief=tk.FLAT,
            bd=2
        )
        self.search_entry.pack(pady=5, fill=tk.X)
        self.search_entry.bind('<Return>', lambda e: self.search_user())  # Enter для поиска

        # ========================================
        # 3. КНОПКА ПОИСКА
        # ========================================
        self.search_btn = tk.Button(
            search_frame,
            text="🔎 НАЙТИ ПОЛЬЗОВАТЕЛЕЙ",
            command=self.search_user,
            bg="#2d5aa0",
            fg="white",
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            padx=20,
            pady=5
        )
        self.search_btn.pack(pady=10)

        # ========================================
        # 4. РЕЗУЛЬТАТЫ ПОИСКА
        # ========================================
        results_frame = tk.LabelFrame(
            self.root,
            text="📋 Результаты поиска (кликните для выбора)",
            padx=10,
            pady=5
        )
        results_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

        tk.Label(results_frame, text=f"Найдено пользователей: 0").pack(anchor=tk.W)

        # Listbox для результатов поиска с прокруткой
        results_scrollbar = tk.Scrollbar(results_frame)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.results_listbox = tk.Listbox(
            results_frame,
            width=55,
            height=10,
            font=("Consolas", 10),
            selectmode=tk.SINGLE,  # Только один выбор
            yscrollcommand=results_scrollbar.set
        )
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.config(command=self.results_listbox.yview)

        # Привязка события выбора
        self.results_listbox.bind('<<ListboxSelect>>', self.on_result_select)

        # ========================================
        # 5. КНОПКА ДОБАВЛЕНИЯ В ИЗБРАННОЕ
        # ========================================
        self.add_fav_btn = tk.Button(
            self.root,
            text="⭐ ДОБАВИТЬ В ИЗБРАННОЕ",
            command=self.add_to_favorites,
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            state=tk.DISABLED,  # Неактивна до выбора
            relief=tk.RAISED,
            padx=20,
            pady=8
        )
        self.add_fav_btn.pack(pady=10)

        # ========================================
        # 6. СПИСОК ИЗБРАННЫХ
        # ========================================
        fav_frame = tk.LabelFrame(
            self.root,
            text="💖 Избранные пользователи (сохранено локально)",
            padx=10,
            pady=5
        )
        fav_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

        # Счетчик избранных
        self.fav_count_label = tk.Label(fav_frame, text=f"Всего избранных: {len(self.favorites)}")
        self.fav_count_label.pack(anchor=tk.W)

        # Listbox избранных с прокруткой
        fav_scrollbar = tk.Scrollbar(fav_frame)
        fav_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.fav_listbox = tk.Listbox(
            fav_frame,
            width=55,
            height=8,
            font=("Consolas", 10),
            yscrollcommand=fav_scrollbar.set
        )
        self.fav_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fav_scrollbar.config(command=self.fav_listbox.yview)

    def search_user(self):
        """
        Выполняет поиск пользователей через GitHub API.
        Проверяет валидность ввода и отображает результаты.
        """
        query = self.search_var.get().strip()

        # ========================================
        # ПРОВЕРКА КОРРЕКТНОСТИ ВВОДА
        # ========================================
        if not query:
            messagebox.showwarning("⚠️ Ошибка ввода", "Поле поиска не должно быть пустым!")
            self.search_entry.focus()  # Фокус на поле ввода
            return

        if len(query) < 2:
            messagebox.showwarning("⚠️ Ошибка ввода", "Запрос должен содержать минимум 2 символа!")
            return

        # Очистка предыдущих результатов
        self.results_listbox.delete(0, tk.END)
        self.selected_result_index = None
        self.add_fav_btn.config(state=tk.DISABLED)

        try:
            # ========================================
            # ЗАПРОС К GITHUB API
            # ========================================
            self.search_btn.config(text="⏳ Поиск...", state=tk.DISABLED)

            url = f"{GITHUB_SEARCH_API}?q={query}&per_page={MAX_RESULTS}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                users = data.get('items', [])

                # Отображение результатов
                self.results_listbox.delete(0, tk.END)
                for i, user in enumerate(users):
                    login = user['login']
                    self.results_listbox.insert(tk.END, f"👤 {login}")

                count = len(users)
                if count == 0:
                    self.results_listbox.insert(tk.END, "❌ Пользователи не найдены")
                    messagebox.showinfo("ℹ️ Результат", f"Пользователи по запросу '{query}' не найдены.")
                else:
                    messagebox.showinfo("✅ Найдено", f"Найдено {count} пользователей!")

            else:
                error_msg = f"API вернул ошибку: {response.status_code}"
                if response.status_code == 403:
                    error_msg += "\n⏰ Превышен лимит запросов (60/час). Подождите!"
                messagebox.showerror("❌ Ошибка API", error_msg)

        except requests.exceptions.Timeout:
            messagebox.showerror("❌ Таймаут", "Превышен лимит времени ожидания ответа.")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("❌ Нет сети", "Проверьте подключение к интернету.")
        except Exception as e:
            messagebox.showerror("❌ Неизвестная ошибка", f"Произошла ошибка: {str(e)}")

        finally:
            # Восстановление кнопки
            self.search_btn.config(text="🔎 НАЙТИ ПОЛЬЗОВАТЕЛЕЙ", state=tk.NORMAL)

    def on_result_select(self, event):
        """
        Обработчик выбора пользователя из списка результатов.
        Активирует кнопку добавления в избранное.
        """
        selection = self.results_listbox.curselection()
        if selection:
            self.selected_result_index = selection[0]
            self.add_fav_btn.config(state=tk.NORMAL)
        else:
            self.selected_result_index = None
            self.add_fav_btn.config(state=tk.DISABLED)

    def add_to_favorites(self):
        """
        Добавляет выбранного пользователя в избранное.
        Проверяет дубликаты и сохраняет в JSON.
        """
        if self.selected_result_index is None:
            messagebox.showwarning("⚠️ Выбор", "Сначала выберите пользователя из результатов!")
            return

        # Получаем логин из отображаемого текста
        selected_text = self.results_listbox.get(self.selected_result_index)
        username = selected_text.split(' ', 1)[1] if ' ' in selected_text else selected_text

        if username in self.favorites:
            messagebox.showinfo("ℹ️ Уже есть", f"👤 @{username} уже в избранном!")
            return

        # Добавление в избранное
        self.favorites.append(username)
        self.save_favorites()
        self.update_fav_listbox()

        messagebox.showinfo(
            "✅ Добавлено!",
            f"Пользователь @{username} добавлен в избранное!\n"
            f"Всего избранных: {len(self.favorites)}"
        )

        # Деактивация кнопки после добавления
        self.add_fav_btn.config(state=tk.DISABLED)

    def load_favorites(self):
        """
        Загружает список избранных пользователей из JSON файла.
        Возвращает пустой список при ошибках.
        """
        if os.path.exists(FAVORITES_FILE):
            try:
                with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except json.JSONDecodeError:
                print("⚠️ Ошибка чтения favorites.json - файл поврежден")
                return []
            except Exception as e:
                print(f"⚠️ Ошибка загрузки избранного: {e}")
                return []
        return []

    def save_favorites(self):
        """
        Сохраняет список избранных в JSON файл с отступами и UTF-8.
        """
        try:
            with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")

    def update_fav_listbox(self):
        """
        Обновляет отображение списка избранных пользователей.
        """
        self.fav_listbox.delete(0, tk.END)
        for user in self.favorites:
            self.fav_listbox.insert(tk.END, f"⭐ {user}")

        self.fav_count_label.config(text=f"Всего избранных: {len(self.favorites)}")


# ========================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = GitHubFinderApp(root)
    root.mainloop()