"""Launcher UI. All preparation and probes run outside the GUI thread."""
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import sys
import time

from . import __version__
from .core import (ROOT, Settings, Runtime, LauncherError, atomic_json, load_settings,
                   inspect, configure_all, replace_server_config)
from .credentials import CredentialError, load_database_password, save_database_password
from .diagnostics import record_exception
from .postgres import PostgresSetupError, ensure_postgres
from .status import ProcessState, inspect_status
from .process_control import prepare_target, close_port_process
from .processes import managed_process_tag
from .appearance import load_dark_mode, save_dark_mode
from .payment import patch_client
from .qt import *

from .theme import (style_sheet, state_colors, palette, navigation_icon, header_icon, set_dark_titlebar,
                    application_icon, set_application_identity, brand_pixmap)


class Worker(QThread):
    progress = Signal(str)
    password_saved = Signal(str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, operation, parent=None, *, password_updates=False, context="后台操作"):
        super().__init__(parent)
        self.operation = operation
        self.password_updates = password_updates
        self.root = getattr(parent, "root", ROOT)
        self.context = context

    def run(self):
        try:
            if self.password_updates:
                result = self.operation(self.progress.emit, self.password_saved.emit)
            else:
                result = self.operation(self.progress.emit)
            self.completed.emit(result)
        except LauncherError as exc:
            saved = record_exception(self.root, exc, context=self.context)
            detail = "" if saved else "\n错误日志无法写入，请检查运行目录权限。"
            self.failed.emit(str(exc) + detail)
        except Exception as exc:
            saved = record_exception(self.root, exc, context=self.context)
            detail = "调用位置见运行日志中的「后台操作错误」。" if saved else "错误日志无法写入，请检查运行目录权限。"
            self.failed.emit(f"操作未完成（{type(exc).__name__}）。请重新检查环境；" + detail)


class NoFocusItemDelegate(QStyledItemDelegate):
    """Suppress cell focus painting even when Qt restores focus from a child/dialog."""
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.state &= ~QStyle.StateFlag.State_HasFocus


class ExpandedPortTable(QTableWidget):
    """Fit all port rows in the page, including wrapped IPv6 and multiple owners."""
    def __init__(self, *args):
        super().__init__(*args)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._fit_pending = False
        self.horizontalHeader().sectionResized.connect(self.schedule_fit)

    def schedule_fit(self, *args):
        if not self._fit_pending:
            self._fit_pending = True
            QTimer.singleShot(0, self.fit_contents)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.schedule_fit()

    def fit_contents(self):
        self._fit_pending = False
        self.resizeRowsToContents()
        for row in range(self.rowCount()):
            button = self.cellWidget(row, 3)
            minimum = max(46, button.sizeHint().height() + 12) if button else 46
            self.setRowHeight(row, max(minimum, self.rowHeight(row)))
        height = self.horizontalHeader().height() + sum(self.rowHeight(row) for row in range(self.rowCount()))
        self.setFixedHeight(height + self.frameWidth() * 2)


class LauncherWindow(QMainWindow):
    def __init__(self, *, preview=False, root=ROOT):
        super().__init__()
        self.root = Path(root)
        self.preview = preview
        self.dark_mode = load_dark_mode(self.root)
        self.state_colors = state_colors(self.dark_mode)
        self.header_controls = []
        self.runtime = Runtime(self.root)
        self.worker = None
        self.status_worker = None
        self.status_again = False
        self.live_snapshot = None
        self.operation_kind = ""
        self.operation_phase = ""
        self.launch_error = ""
        self.action_buttons = []
        self.checks = []
        self.load_error = ""
        try:
            self.settings = load_settings(self.root)
        except LauncherError as exc:
            self.settings = Settings()
            self.load_error = str(exc)
        self.setWindowTitle("MasterofGarden · 本地启动器")
        self.setWindowIcon(application_icon())
        self.resize(1160, 840)
        self.setMinimumSize(1020, 760)
        self.setStyleSheet(style_sheet(self.dark_mode))
        shell = QWidget()
        shell.setObjectName("shell")
        self.setCentralWidget(shell)
        outer = QHBoxLayout(shell)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(215)
        navigation = QVBoxLayout(sidebar)
        navigation.setContentsMargins(16, 28, 16, 22)
        navigation.setSpacing(9)
        brand_row = QHBoxLayout()
        mark = self.label("", "brandMark")
        mark.setFixedSize(42, 42)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setPixmap(brand_pixmap())
        brand_row.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(3)
        brand_text.addWidget(self.label("MasterofGarden", "brand"))
        brand_text.addWidget(self.label("LOCAL LAUNCHER", "eyebrow"))
        brand_row.addLayout(brand_text)
        navigation.addLayout(brand_row)
        navigation.addSpacing(27)
        navigation.addWidget(self.label("工作空间", "muted"))
        self.stack = QStackedWidget()
        self.nav = []
        for index, name in enumerate(("开始游戏", "环境准备", "运行日志", "设置", "关于")):
            button = QPushButton(name)
            button.setObjectName("nav")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIcon(navigation_icon(index, dark=self.dark_mode))
            button.clicked.connect(lambda checked=False, i=index: self.go(i))
            navigation.addWidget(button)
            self.nav.append(button)
        navigation.addStretch()
        note = QFrame()
        note.setObjectName("sidebarNote")
        note_layout = QVBoxLayout(note)
        note_layout.setContentsMargins(14, 14, 14, 14)
        note_layout.addWidget(self.label("你的本地冒险", "cardTitle"))
        self.session_badge = self.label("尚未启动", "badge")
        note_layout.addWidget(self.session_badge)
        navigation.addWidget(note)
        navigation.addSpacing(6)
        navigation.addWidget(self.label("版本  /  v" + __version__, "muted"))
        outer.addWidget(sidebar)
        outer.addWidget(self.stack, 1)
        self._home()
        self._environment()
        self._logs()
        self._settings()
        self._about()
        self.go(0)
        self.apply_theme()
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(2000)
        self.status_timer.timeout.connect(self.refresh_runtime_status)
        for control in (*self.service_port_fields.values(), self.dbport):
            control.valueChanged.connect(self.ports_changed)
        if preview:
            self.display_checks(inspect(self.settings, self.root, network=False))
        else:
            self.status_timer.start()
            QTimer.singleShot(0, self.refresh_runtime_status)
            QTimer.singleShot(0, self.resume_database)

    @staticmethod
    def label(text, name=""):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setObjectName(name)
        return label

    def page(self, title, subtitle):
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(18)
        heading = QHBoxLayout()
        heading.addWidget(self.label(title, "title"), 1)
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(2)
        heading.addLayout(toolbar)
        actions = {}
        for kind, title in (("gm", "打开 GM 界面（暂未开放）"),
                            ("theme", "切换日间模式" if self.dark_mode else "切换夜间模式"),
                            ("settings", "打开设置")):
            button = QPushButton()
            button.setObjectName("headerAction")
            button.setFixedSize(30, 30)
            button.setIconSize(QSize(20, 20))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(title)
            button.setAccessibleName(title)
            if kind == "gm":
                button.setEnabled(False)
            elif kind == "theme":
                button.clicked.connect(lambda checked=False: self.toggle_theme())
            else:
                button.clicked.connect(lambda checked=False: self.go(3))
            icon = "sun" if self.dark_mode else "moon"
            button.setIcon(header_icon(icon if kind == "theme" else kind, self.dark_mode))
            actions[kind] = button
            toolbar.addWidget(button)
        self.header_controls.append(actions)
        layout.addLayout(heading)
        layout.addWidget(self.label(subtitle, "subtitle"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        self.stack.addWidget(scroll)
        return layout

    def card(self, layout, title):
        card = QFrame()
        card.setObjectName("card")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.label(title, "cardHeader"))
        body = QFrame()
        body.setObjectName("cardBody")
        inner = QVBoxLayout(body)
        inner.setContentsMargins(18, 16, 18, 16)
        inner.setSpacing(13)
        outer.addWidget(body)
        layout.addWidget(card)
        return inner

    def button(self, text, callback, primary=False):
        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            button.setObjectName("primary")
        button.clicked.connect(lambda checked=False: callback())
        self.action_buttons.append(button)
        return button

    def go(self, index):
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav):
            button.setChecked(i == index)
            button.setIcon(navigation_icon(i, active=i == index, dark=self.dark_mode))

    def apply_theme(self):
        self.state_colors = state_colors(self.dark_mode)
        style = style_sheet(self.dark_mode)
        # Application palette/style also reaches Qt popups and dialogs.
        application = QApplication.instance()
        application.setPalette(palette(self.dark_mode))
        application.setStyleSheet(style)
        self.setStyleSheet(style)
        set_dark_titlebar(self, self.dark_mode)
        for actions in self.header_controls:
            title = "切换日间模式" if self.dark_mode else "切换夜间模式"
            actions["theme"].setToolTip(title)
            actions["theme"].setAccessibleName(title)
            for kind, button in actions.items():
                icon = ("sun" if self.dark_mode else "moon") if kind == "theme" else kind
                button.setIcon(header_icon(icon, self.dark_mode))
        self.go(self.stack.currentIndex())
        for state, label in self.metrics.items():
            label.setStyleSheet("color: " + self.state_colors[state] + ";")
        for row, check in enumerate(self.checks):
            item = self.table.item(row, 1)
            if item:
                item.setForeground(QColor(self.state_colors[check.state]))
        if self.live_snapshot:
            for tag, item in self.live_snapshot.components.items():
                label = self.component_labels[tag][0]
                color = self.component_color(item)
                label.setStyleSheet("color: " + color + ";")
            for row, item in enumerate(self.live_snapshot.ports):
                cell = self.port_table.item(row, 1)
                if cell:
                    cell.setForeground(QColor(self.state_colors[item.state]))
        self.port_table.schedule_fit()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        if not self.preview:
            try:
                save_dark_mode(self.root, self.dark_mode)
            except (OSError, ValueError):
                self.activity.appendPlainText("外观已切换，但模式偏好未能保存；下次打开将使用之前的模式。")

    def component_color(self, item):
        if item.text in ("未启动", "已停止", "已退出", "未监听"):
            return self.state_colors["warn"]
        return self.state_colors[item.state]

    def _home(self):
        layout = self.page("开始游戏", "从这里准备环境，继续你的本地冒险。")
        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 16, 24, 16)
        hero_layout.setSpacing(12)
        upper = QHBoxLayout()
        content = QVBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.label("本地游戏", "heroTitle"))
        content.addWidget(self.label("准备环境后即可启动，运行情况和端口占用见下方。", "muted"))
        upper.addLayout(content, 1)
        hero_layout.addLayout(upper)
        status_row = QHBoxLayout()
        self.summary = self.label("正在检查环境…", "cardTitle")
        status_row.addWidget(self.summary, 1)
        self.readiness = self.label("检查中", "badge")
        status_row.addWidget(self.readiness)
        hero_layout.addLayout(status_row)
        row = QHBoxLayout()
        self.start_button = self.button("启动本地游戏", self.start_game, True)
        self.start_button.setMinimumWidth(168)
        self.start_button.setEnabled(False)
        row.addWidget(self.start_button)
        row.addWidget(self.button("检查准备情况", lambda: (self.go(1), self.run_checks())))
        self.stop_button = self.button("停止本次启动", self.stop_game)
        self.stop_button.setObjectName("danger")
        self.stop_button.setEnabled(False)
        row.addWidget(self.stop_button)
        row.addStretch()
        hero_layout.addLayout(row)
        layout.addWidget(hero)
        self._runtime_panel(layout)
        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.metrics = {}
        for state, title in (("pass", "检查通过"), ("warn", "等待确认"), ("error", "需要处理")):
            inner = self.card(metrics, title)
            number = self.label("—", "metric")
            number.setStyleSheet("color: " + self.state_colors[state] + ";")
            inner.addWidget(number)
            self.metrics[state] = number
        layout.addLayout(metrics)
        layout.addWidget(self.label("首次使用 · 三步准备", "cardTitle"))
        steps = QHBoxLayout()
        steps.setSpacing(12)
        for index, (title, description, action, destination) in enumerate((
            ("选择本地文件", "选择游戏入口和接入工具，Python 环境自动管理。", "打开设置  →", 3),
            ("准备运行环境", "填写数据库密码，一键准备依赖、配置和数据库。", "准备环境  →", 1),
            ("检查并启动", "查看检查结果，完成准备后回到这里启动游戏。", "查看检查  →", 1),
        ), 1):
            inner = self.card(steps, title)
            number = self.label(f"0{index}", "stepNumber")
            number.setFixedSize(34, 30)
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inner.insertWidget(0, number)
            inner.addWidget(self.label(description, "muted"))
            inner.addStretch()
            inner.addWidget(self.button(action, lambda i=destination: self.go(i)))
        layout.addLayout(steps)
        help_row = QHBoxLayout()
        help_row.addWidget(self.label("启动与配置的详细信息，可在运行日志中查看。", "muted"), 1)
        help_row.addWidget(self.button("查看运行日志  →", lambda: self.go(2)))
        layout.addLayout(help_row)
        layout.addStretch()

    def _runtime_panel(self, layout):
        panel = self.card(layout, "当前启动情况")
        row = QHBoxLayout()
        self.live_summary = self.label("未启用运行监测" if self.preview else "正在读取运行状态…", "cardTitle")
        row.addWidget(self.live_summary, 1)
        panel.addLayout(row)
        self.live_phase = self.label("启动阶段、进程退出和端口占用会在这里显示。", "muted")
        panel.addWidget(self.live_phase)
        components = QHBoxLayout()
        components.setSpacing(14)
        self.component_labels = {}
        for tag, title in (("server", "服务端"), ("proxy", "本地接入"), ("game", "游戏"), ("database", "数据库")):
            column = QVBoxLayout()
            column.addWidget(self.label(title, "muted"))
            status = self.label("未检测", "cardTitle")
            detail = self.label("—", "muted")
            column.addWidget(status)
            column.addWidget(detail)
            components.addLayout(column, 1)
            self.component_labels[tag] = (status, detail)
        panel.addLayout(components)
        port_frame = QFrame()
        port_frame.setObjectName("portList")
        port_layout = QVBoxLayout(port_frame)
        port_layout.setContentsMargins(8, 8, 8, 8)
        self.port_table = ExpandedPortTable(4, 4)
        self.port_table.setObjectName("portTable")
        self.port_table.setHorizontalHeaderLabels(("用途 / 端口", "当前状态", "占用进程 / 监听地址", "操作"))
        self.port_table.verticalHeader().setVisible(False)
        self.port_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.port_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.port_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.port_table.setItemDelegate(NoFocusItemDelegate(self.port_table))
        self.port_table.setShowGrid(False)
        self.port_table.setWordWrap(True)
        self.port_table.setAlternatingRowColors(False)
        self.port_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.port_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.port_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.port_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.port_table.setColumnWidth(0, 142)
        self.port_table.setColumnWidth(1, 120)
        self.port_table.setColumnWidth(3, 108)
        self.port_buttons = []
        for row in range(4):
            for column, value in enumerate(("等待检测", "未检测", "未启用实时监测" if self.preview else "正在读取…")):
                self.port_table.setItem(row, column, QTableWidgetItem(value))
            self.port_table.setRowHeight(row, 46)
            button = self.button("关闭程序", lambda index=row: self.choose_port_owner(index))
            button.setObjectName("danger")
            button.setEnabled(False)
            self.port_buttons.append(button)
            self.port_table.setCellWidget(row, 3, button)
        self.port_table.schedule_fit()
        port_layout.addWidget(self.port_table)
        panel.addWidget(port_frame)

    def choose_port_owner(self, row):
        if self.preview or self.worker is not None or self.live_snapshot is None:
            return
        port = self.monitored_ports()[row]
        targets = dict(self.live_snapshot.port_processes.get(port, {}))
        if len(targets) == 1:
            self.close_port_owner(port, next(iter(targets)))
        elif targets:
            menu = QMenu(self)
            for pid, name in sorted(targets.items()):
                action = menu.addAction(f"{name} · PID {pid}")
                action.triggered.connect(lambda checked=False, pid=pid: self.close_port_owner(port, pid))
            menu.exec(self.port_buttons[row].mapToGlobal(self.port_buttons[row].rect().bottomLeft()))
            menu.deleteLater()

    def close_port_owner(self, port, pid):
        if self.preview or self.worker is not None:
            return
        try:
            target = prepare_target(port, pid)
            tag = managed_process_tag(self.runtime.children, pid)
        except LauncherError as exc:
            self.failure(str(exc))
            self.refresh_runtime_status()
            return
        except OSError:
            self.failure("无法确认占用进程的归属，请等待状态自动更新后重试。")
            return
        impact = "将结束该程序，所有相关端口和连接都会断开，未保存内容可能丢失。"
        if target.name.casefold() == "postgres.exe":
            impact = "将正常停止整个数据库实例，断开其所有客户端连接，未提交的事务会回滚。\n本次启动的游戏和服务也会停止。"
        elif tag == "server":
            impact += "\n本次启动的游戏和本地接入也会停止。"
        elif tag == "proxy":
            impact += "\n本次启动的游戏也会停止。"
        answer = QMessageBox.question(self, "关闭端口占用程序",
            f"程序：{target.name}\nPID：{pid}\n端口：{port}\n\n{impact}\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.run_job(lambda progress: close_port_process(target, self.runtime, progress),
                     lambda result: QTimer.singleShot(100, self.run_checks), kind="close")

    def refresh_runtime_status(self):
        if self.preview or self.status_worker is not None:
            return
        now = time.monotonic()
        processes = {tag: ProcessState(child.pid, child.poll(),
                        max(0, now - self.runtime.started_at.get(tag, now)), tag in self.runtime.stopped_tags)
                     for tag, child in tuple(self.runtime.children.items())}
        ports = self.monitored_ports()
        api_port, proxy_port, web_port, dbport = ports
        self.status_worker = Worker(lambda progress: inspect_status(self.root, dbport, processes,
            api_port=api_port, proxy_port=proxy_port, web_port=web_port), self)
        self.status_worker.completed.connect(lambda snapshot: self.accept_runtime_status(snapshot, ports, processes))
        self.status_worker.failed.connect(lambda message: self.live_phase.setText("运行监测暂不可用，稍后自动重试。"))
        self.status_worker.finished.connect(self.status_finished)
        self.status_worker.start()

    def accept_runtime_status(self, snapshot, ports, processes):
        # Support existing database-only snapshot callers using the default service ports.
        if isinstance(ports, int):
            ports = (*self.settings.service_ports, ports)
        captured = {tag: (process.pid, process.exit_code, process.stopped) for tag, process in processes.items()}
        current = {tag: (child.pid, child.poll(), tag in self.runtime.stopped_tags)
                   for tag, child in tuple(self.runtime.children.items())}
        if ports != self.monitored_ports() or captured != current:
            self.status_again = True
            return
        self.display_runtime_status(snapshot)

    def status_finished(self):
        worker = self.status_worker
        self.status_worker = None
        if worker is not None:
            worker.deleteLater()
        if self.status_again:
            self.status_again = False
            QTimer.singleShot(0, self.refresh_runtime_status)

    def display_runtime_status(self, snapshot):
        self.live_snapshot = snapshot
        for tag, item in snapshot.components.items():
            status, detail = self.component_labels[tag]
            status.setText(item.text)
            color = self.component_color(item)
            status.setStyleSheet("color: " + color + ";")
            detail.setText(item.detail or "—")
        for row, item in enumerate(snapshot.ports):
            for column, value in enumerate((item.title, item.text, item.detail)):
                cell = QTableWidgetItem(value)
                cell.setToolTip(value)
                if column == 1:
                    cell.setForeground(QColor(self.state_colors[item.state]))
                self.port_table.setItem(row, column, cell)
        self.port_table.schedule_fit()
        self.update_runtime_summary()
        self.update_launch_buttons()

    def update_runtime_summary(self):
        snapshot = self.live_snapshot
        if self.worker is not None:
            text = {"start": "正在启动游戏", "stop": "正在停止本次启动", "configure": "正在配置环境",
                    "database": "正在恢复数据库", "close": "正在关闭端口程序", "check": "正在检查环境",
                    "payment": "正在修改客户端 DLL"}.get(self.operation_kind, "操作进行中")
            state = "warn"
            phase = self.operation_phase or "请稍候，运行状态持续更新。"
        elif self.launch_error:
            text, state, phase = "启动未完成", "error", self.launch_error
        elif snapshot is None:
            text, state, phase = "未启用运行监测" if self.preview else "等待状态更新", "warn", "运行状态和端口信息将在此显示。"
        elif snapshot.conflicts:
            text, state, phase = "检测到端口冲突", "error", "查看下方占用进程，可点击「关闭程序」确认处理后再启动。"
        elif any(item.state == "error" for item in snapshot.components.values()):
            text, state, phase = "有进程异常退出", "error", "退出码见组件状态，详细输出见运行日志。"
        elif snapshot.game_running:
            text, state, phase = ("其他游戏实例运行中", "warn", "该游戏不由本次启动器管理，停止按钮只处理本次启动。") if snapshot.components["game"].text == "其他实例运行中" else (
                "游戏运行中", "pass", "游戏进程正在运行，详细输出可在运行日志中查看。")
        elif snapshot.owned_running:
            text, state, phase = "本地服务运行中", "pass", "游戏未运行，可继续启动或停止本次服务。"
        elif snapshot.unavailable:
            text, state, phase = "运行监测暂不可用", "warn", "稍后自动重试。"
        else:
            text, state, phase = "游戏未启动", "warn", "完成环境准备后即可启动；数据库可以独立运行。"
        self.live_summary.setText(text)
        self.live_phase.setText(phase)
        self.session_badge.setText(text)
        self.session_badge.setProperty("state", state)
        self.session_badge.style().unpolish(self.session_badge)
        self.session_badge.style().polish(self.session_badge)

    def update_launch_buttons(self):
        owned = self.runtime.owned()
        running = "game" in owned or bool(self.live_snapshot and self.live_snapshot.game_running)
        conflict = bool(self.live_snapshot and self.live_snapshot.conflicts)
        ready = bool(self.checks) and not any(check.state == "error" for check in self.checks) and not self.load_error
        self.start_button.setEnabled(self.worker is None and ready and not running and not conflict)
        self.stop_button.setEnabled(self.worker is None and bool(owned))
        for button in (self.patch_dll_button, self.restore_dll_button):
            button.setEnabled(not self.preview and self.worker is None and not running)
            button.setToolTip("请先退出游戏，再修改或恢复 DLL。" if running else "使用设置页选择的游戏入口，保留原始 DLL 备份。")
        ports = self.monitored_ports()
        ports_valid = len(set(ports)) == len(ports)
        for control in (*self.service_port_fields.values(), self.dbport):
            control.setEnabled(self.worker is None and not owned)
            control.setToolTip("请先停止本次启动，再修改端口。" if owned else "端口范围 1–65535，各端口不能重复。")
        for button, port in zip(self.port_buttons, ports):
            targets = self.live_snapshot.port_processes.get(port, {}) if self.live_snapshot else {}
            button.setEnabled(not self.preview and self.worker is None and ports_valid and bool(targets))
            button.setText("选择程序…" if len(targets) > 1 else "关闭程序")
            button.setToolTip("关闭此端口的占用程序，执行前确认进程和影响。" if targets else "当前没有可关闭的监听进程。")
        self.start_button.setText("启动中…" if self.operation_kind == "start" and self.worker else
                                  "游戏运行中" if running else "启动本地游戏")

    def _environment(self):
        layout = self.page("环境准备", "检查启动游戏所需的程序、依赖与本机配置。")
        row = QHBoxLayout()
        row.addWidget(self.button("重新检查", self.run_checks))
        row.addWidget(self.button("一键完成配置", self.prepare_config, True))
        row.addWidget(self.button("选择本地文件", lambda: self.go(3)))
        row.addStretch()
        layout.addLayout(row)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(("检查项目", "状态", "结果与处理方法"))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setItemDelegate(NoFocusItemDelegate(self.table))
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setMinimumHeight(340)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 165)
        self.table.setColumnWidth(1, 80)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.label("先在设置页填写连接信息和密码，再一键准备 Python 环境、依赖、服务配置与数据库。", "muted"))

    def _logs(self):
        layout = self.page("运行日志", "查看启动、配置和运行中的输出，日志自动更新。")
        self.log_sources = {
            "启动器操作": None,
            "服务端": "server.log",
            "本地接入": "proxy.log",
            "游戏进程": "game.log",
            "服务端环境配置": "python-server-setup.log",
            "界面环境配置": "python-launcher-setup.log",
            "数据库程序": "postgres.log",
            "数据库初始化": "database-setup.log",
            "后台操作错误": "launcher-errors.log",
        }
        self.log_snapshot = None
        row = QHBoxLayout()
        row.addWidget(self.label("日志来源", "muted"))
        self.log_source = QComboBox()
        self.log_source.addItems(list(self.log_sources))
        self.log_source.setMinimumWidth(190)
        row.addWidget(self.log_source)
        row.addStretch()
        self.follow_logs = QCheckBox("跟随最新输出")
        self.follow_logs.setChecked(True)
        row.addWidget(self.follow_logs)
        refresh = QPushButton("刷新")
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.clicked.connect(lambda: self.refresh_logs(force=True))
        row.addWidget(refresh)
        layout.addLayout(row)
        self.log_stack = QStackedWidget()
        self.activity = self.log_editor("启动器操作结果将显示在这里。")
        self.file_log = self.log_editor("此来源暂无日志，启动或配置后会自动显示。")
        self.log_stack.addWidget(self.activity)
        self.log_stack.addWidget(self.file_log)
        self.log_stack.setMinimumHeight(400)
        layout.addWidget(self.log_stack, 1)
        self.log_status = self.label("显示本次打开启动器后的操作记录", "muted")
        layout.addWidget(self.log_status)
        self.log_source.currentIndexChanged.connect(lambda: self.refresh_logs(force=True))
        self.follow_logs.toggled.connect(self.update_log_follow)
        self.log_timer = QTimer(self)
        self.log_timer.setInterval(1000)
        self.log_timer.timeout.connect(self.refresh_logs)
        if not self.preview:
            self.log_timer.start()

    def log_editor(self, placeholder):
        editor = QPlainTextEdit()
        editor.setObjectName("log")
        editor.setReadOnly(True)
        editor.setMaximumBlockCount(2000)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        editor.setPlaceholderText(placeholder)
        return editor

    def update_log_follow(self):
        if self.follow_logs.isChecked():
            for editor in (self.activity, self.file_log):
                bar = editor.verticalScrollBar()
                bar.setValue(bar.maximum())

    def append_activity(self, text):
        bar = self.activity.verticalScrollBar()
        position = bar.value()
        self.activity.appendPlainText(f"[{datetime.now():%H:%M:%S}] {text}")
        if self.follow_logs.isChecked():
            bar.setValue(bar.maximum())
        else:
            bar.setValue(position)
        if self.worker is not None:
            self.operation_phase = text
            self.update_runtime_summary()

    def refresh_logs(self, force=False):
        filename = self.log_sources[self.log_source.currentText()]
        if filename is None:
            self.log_stack.setCurrentIndex(0)
            self.log_status.setText("显示本次打开启动器后的操作记录")
            self.update_log_follow()
            return
        self.log_stack.setCurrentIndex(1)
        # Bound each read and display; never load an entire long-running log.
        path = self.root / "runtime/logs" / filename
        limit = 256 * 1024
        try:
            # Refuse paths that leave this project, including linked directories.
            path.resolve().relative_to(self.root.resolve())
            stat = path.stat()
            snapshot = (filename, stat.st_mtime_ns, stat.st_size)
            if not force and snapshot == self.log_snapshot:
                return
            with path.open("rb") as source:
                offset = max(0, stat.st_size - limit)
                source.seek(offset)
                content = source.read(limit)
            if offset and b"\n" in content:
                content = content.partition(b"\n")[2]
            value = content.decode("utf-8", errors="replace")
            status = f"runtime/logs/{filename} · 最近 256 KB · 每秒更新"
        except FileNotFoundError:
            snapshot, value = (filename, None), ""
            status = f"runtime/logs/{filename} · 暂无日志，等待输出"
        except (OSError, ValueError):
            snapshot, value = None, ""
            status = "日志暂时无法读取，请检查文件权限或路径。"
        bar = self.file_log.verticalScrollBar()
        position = bar.value()
        self.file_log.setPlainText(value)
        bar.setValue(bar.maximum() if self.follow_logs.isChecked() else position)
        self.log_snapshot = snapshot
        self.log_status.setText(status)

    def _settings(self):
        layout = self.page("设置", "管理游戏入口、本地接入工具和数据库连接。")
        form = self.card(layout, "本地文件")
        self.fields = {}
        for key, title, placeholder in (
            ("game_exe", "游戏入口", "选择 MasterofGarden.exe"),
            ("proxy_exe", "接入工具", "选择 mitmweb.exe"),
        ):
            row = QHBoxLayout()
            label = QLabel(title)
            label.setFixedWidth(88)
            row.addWidget(label)
            edit = QLineEdit(getattr(self.settings, key))
            edit.setPlaceholderText(placeholder)
            self.fields[key] = edit
            row.addWidget(edit, 1)
            row.addWidget(self.button("选择…", lambda k=key: self.pick(k)))
            form.addLayout(row)
        form.addWidget(self.label("Python 环境由启动器自动管理，点击「一键完成配置」即可准备。", "muted"))
        client = self.card(layout, "客户端 DLL")
        client.addWidget(self.label("使用上方选择的游戏入口，为本地支付启用客户端适配；修改前自动备份原始 DLL。", "muted"))
        client_row = QHBoxLayout()
        self.patch_dll_button = self.button("修改 DLL", self.modify_client_dll, True)
        self.restore_dll_button = self.button("恢复 DLL", lambda: self.modify_client_dll(restore=True))
        client_row.addWidget(self.patch_dll_button)
        client_row.addWidget(self.restore_dll_button)
        client_row.addStretch()
        client.addLayout(client_row)
        ports = self.card(layout, "服务端口")
        port_grid = QGridLayout()
        port_grid.setHorizontalSpacing(16)
        port_grid.setVerticalSpacing(10)
        self.service_port_fields = {}
        for column, (key, title) in enumerate((("api_port", "API 服务"), ("proxy_port", "本地接入"),
                                              ("web_port", "接入管理"))):
            port_grid.addWidget(self.label(title, "muted"), 0, column)
            control = self.port_input(getattr(self.settings, key))
            control.setAccessibleName(title + "端口")
            self.service_port_fields[key] = control
            port_grid.addWidget(control, 1, column)
            port_grid.setColumnStretch(column, 1)
        ports.addLayout(port_grid)
        db = self.card(layout, "独立数据库")
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        for column, (key, title) in enumerate((("dbname", "数据库名称"), ("dbuser", "用户名"))):
            grid.addWidget(self.label(title, "muted"), 0, column)
            edit = QLineEdit(getattr(self.settings, key))
            self.fields[key] = edit
            grid.addWidget(edit, 1, column)
            grid.setColumnStretch(column, 1)
        grid.addWidget(self.label("端口", "muted"), 0, 2)
        self.dbport = self.port_input(self.settings.dbport)
        self.dbport.setMinimumWidth(105)
        grid.addWidget(self.dbport, 1, 2)
        db.addLayout(grid)
        password_row = QHBoxLayout()
        password_row.addWidget(self.label("数据库密码", "muted"))
        self.db_password = QLineEdit()
        self.db_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_password.setPlaceholderText("已有数据库填写密码；新建本项目实例可自动生成")
        self.db_password.setAccessibleName("数据库密码")
        try:
            self.db_password.setText(load_database_password(self.root))
        except CredentialError as exc:
            self.load_error = str(exc)
        password_row.addWidget(self.db_password, 1)
        self.show_password = QCheckBox("显示密码")
        self.show_password.toggled.connect(lambda visible: self.db_password.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password))
        password_row.addWidget(self.show_password)
        db.addLayout(password_row)
        row = QHBoxLayout()
        row.addWidget(self.button("保存设置", self.save_settings, True))
        row.addWidget(self.button("一键完成配置", self.prepare_config, True))
        row.addWidget(self.button("备份并更新服务配置", self.update_config))
        row.addStretch()
        layout.addLayout(row)
        layout.addWidget(self.label("设置保存在本机；保存后可在环境准备页确认配置是否一致。", "muted"))
        layout.addStretch()

    def _about(self):
        layout = self.page("关于", "项目说明、开源许可、免责声明与联系方式。")
        project = self.card(layout, "MasterofGarden")
        project.addWidget(self.label("本地启动器 · v" + __version__, "cardTitle"))
        project.addWidget(self.label("技术栈：Python · Qt · PostgreSQL · mitmproxy\n"
                                     "Vibe Coding — 使用 GPT-6.1 Sol", "muted"))

        license_card = self.card(layout, "开源许可")
        license_card.addWidget(self.label("MIT OR GPL-3.0-only", "cardTitle"))
        license_card.addWidget(self.label("本项目有权授权的代码与文档采用双重许可。你可以选择 MIT 或 GNU GPL v3.0 使用、修改和再分发，并遵守所选许可及第三方组件的适用条款。", "muted"))
        license_card.addWidget(self.label("© 2026 MasterofGarden contributors · 软件按现状提供，不作保证。", "muted"))
        license_row = QHBoxLayout()
        for filename, title in (("LICENSE-MIT", "查看 MIT"), ("LICENSE-GPL-3.0", "查看 GPL v3"),
                                ("LICENSE", "许可范围"), ("THIRD_PARTY_NOTICES.md", "第三方声明")):
            license_row.addWidget(self.button(title, lambda f=filename, t=title: self.show_license_document(f, t)))
        license_row.addStretch()
        license_card.addLayout(license_row)

        disclaimer = self.card(layout, "免责声明")
        for title, text in (
            ("非官方项目", "本项目为独立开发的非官方本地启动器，不代表游戏开发商、发行商或运营方。"),
            ("资源与权利", "游戏名称、商标、客户端、美术、音频及本启动器使用的窗口和侧栏图标，其权利归各自权利人所有。项目开源许可不授予上述资源的使用或再分发权利。本项目为非官方项目，请自行合法取得客户端及相关授权。"),
            ("使用范围", "本项目供学习、研究与本地体验使用。请遵守适用法律及相关协议，不用于侵权、未经授权的商业用途或干扰他人服务。"),
        ):
            disclaimer.addWidget(self.label(title, "cardTitle"))
            disclaimer.addWidget(self.label(text, "muted"))

        contact = self.card(layout, "联系方式")
        contact.addWidget(self.label("如需反馈问题或联系项目维护者，请使用以下邮箱。", "muted"))
        self.contact_email = self.label("498618557@qq.com", "cardTitle")
        self.contact_email.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                                   Qt.TextInteractionFlag.TextSelectableByKeyboard)
        contact.addWidget(self.contact_email)
        layout.addStretch()

    def show_license_document(self, filename, title):
        if filename not in {"LICENSE-MIT", "LICENSE-GPL-3.0", "LICENSE", "THIRD_PARTY_NOTICES.md"}:
            return
        directory = "docs" if filename == "THIRD_PARTY_NOTICES.md" else "licenses"
        path = Path(__file__).resolve().parents[1] / directory / filename
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            QMessageBox.warning(self, "许可文件无法读取", "请检查启动器中的许可文件是否齐全。")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(820, 640)
        layout = QVBoxLayout(dialog)
        viewer = QTextBrowser()
        viewer.setReadOnly(True)
        viewer.setOpenExternalLinks(True)
        viewer.setSearchPaths([str(path.parent)])
        viewer.document().setBaseUrl(QUrl.fromLocalFile(str(path)))
        if path.suffix == ".md":
            viewer.setMarkdown(text)
        else:
            viewer.setFont(QFont("Consolas", 10))
            viewer.setPlainText(text)
        layout.addWidget(viewer)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()
        dialog.deleteLater()

    @staticmethod
    def port_input(value):
        control = QSpinBox()
        control.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        control.setRange(1, 65535)
        control.setValue(value)
        return control

    def port_values(self):
        return (*(self.service_port_fields[key].value() for key in ("api_port", "proxy_port", "web_port")),
                self.dbport.value())

    def monitored_ports(self):
        if self.runtime.owned() and self.runtime.running_ports is not None:
            return self.runtime.running_ports
        return self.port_values()

    def ports_changed(self, *args):
        self.checks = []
        self.table.setRowCount(0)
        for label in self.metrics.values():
            label.setText("—")
        self.summary.setText("端口设置已更改，请保存后检查。")
        self.readiness.setText("待检查")
        self.readiness.setProperty("state", "warn")
        self.readiness.style().unpolish(self.readiness)
        self.readiness.style().polish(self.readiness)
        self.live_snapshot = None
        self.update_launch_buttons()
        self.update_runtime_summary()
        self.refresh_runtime_status()

    def form_settings(self):
        return Settings(**{key: edit.text().strip() for key, edit in self.fields.items()},
                        **{key: control.value() for key, control in self.service_port_fields.items()},
                        dbport=self.dbport.value()).validate()

    def save_password(self):
        try:
            save_database_password(self.root, self.db_password.text())
        except CredentialError as exc:
            raise LauncherError(str(exc)) from None

    def resume_database(self):
        if self.preview:
            return
        if self.load_error:
            self.failure("设置或密码读取失败，已暂停数据库自动恢复。请先在设置页确认并保存连接信息。\n" + self.load_error)
            return
        if not (self.root / "runtime/postgres/PG_VERSION").is_file():
            self.run_checks()
            return
        settings = self.settings
        password = self.db_password.text()
        def operation(progress):
            try:
                ensure_postgres(self.root, settings.dbport, settings.dbuser, password, progress)
            except PostgresSetupError as exc:
                raise LauncherError(str(exc)) from None
        self.run_job(operation, lambda result: QTimer.singleShot(100, self.run_checks), kind="database")

    def pick(self, key):
        path = QFileDialog.getOpenFileName(self, "选择本地程序", "", "程序 (*.exe);;所有文件 (*)",
                                           options=QFileDialog.Option.DontUseNativeDialog)[0]
        if path:
            self.fields[key].setText(path)

    def modify_client_dll(self, *, restore=False):
        if self.preview or self.worker is not None:
            return
        if "game" in self.runtime.owned() or (self.live_snapshot and self.live_snapshot.game_running):
            self.failure("请先退出游戏，再修改或恢复 DLL。")
            return
        game = self.fields["game_exe"].text().strip()
        game = Path(game) if game else self.root / "client/MasterofGarden.exe"
        self.go(2)
        self.run_job(lambda progress: patch_client(game, self.root, restore=restore, progress=progress),
                     self.append_activity, kind="payment")

    def run_job(self, operation, complete, *, kind="check", password_updates=False):
        if self.worker is not None:
            return
        self.operation_kind = kind
        self.operation_phase = ""
        if kind in ("start", "stop", "configure", "close"):
            self.launch_error = ""
        for button in self.action_buttons:
            button.setEnabled(False)
        for control in (*self.fields.values(), *self.service_port_fields.values(), self.dbport, self.db_password):
            control.setEnabled(False)
        self.worker = Worker(operation, self, password_updates=password_updates, context=kind)
        self.worker.progress.connect(self.append_activity)
        self.worker.password_saved.connect(self.db_password.setText)
        self.worker.completed.connect(complete)
        self.worker.failed.connect(self.failure)
        self.worker.finished.connect(self.job_finished)
        self.update_runtime_summary()
        self.worker.start()

    def job_finished(self):
        worker = self.worker
        self.worker = None
        self.operation_kind = ""
        if worker is not None:
            worker.deleteLater()
        for button in self.action_buttons:
            button.setEnabled(True)
        for control in (*self.fields.values(), *self.service_port_fields.values(), self.dbport, self.db_password, self.show_password):
            control.setEnabled(True)
        self.update_launch_buttons()
        self.update_runtime_summary()
        self.refresh_runtime_status()

    def failure(self, text):
        if self.operation_kind == "start":
            self.launch_error = text
        self.append_activity(text)
        self.go(2)

    def run_checks(self):
        try:
            settings = self.form_settings()
        except LauncherError as exc:
            self.failure(str(exc))
            return
        owned = self.runtime.owned()
        roots = {tag: child.pid for tag, child in tuple(self.runtime.children.items()) if tag in owned}
        password = self.db_password.text()
        self.run_job(lambda progress: inspect(settings, self.root, network=not self.preview, owned=owned,
                                             password=password, owned_processes=roots), self.display_checks)

    def display_checks(self, checks):
        self.checks = checks
        errors = sum(c.state == "error" for c in checks)
        warnings = sum(c.state == "warn" for c in checks)
        state = "error" if errors or self.load_error else "warn" if warnings else "pass"
        if errors:
            summary = f"{errors} 项需要处理" + (f" · {warnings} 项待确认" if warnings else "")
        elif self.load_error:
            summary = "设置读取失败，请检查设置。"
        elif warnings:
            summary = f"环境检查完成 · {warnings} 项待确认"
        else:
            summary = "环境检查通过"
        self.summary.setText(summary)
        self.readiness.setText({"error": "需要准备", "warn": "待确认", "pass": "已就绪"}[state])
        self.readiness.setProperty("state", state)
        self.readiness.style().unpolish(self.readiness)
        self.readiness.style().polish(self.readiness)
        for key, number in self.metrics.items():
            number.setText(str(sum(check.state == key for check in checks)))
        self.table.setRowCount(len(checks))
        names = {"pass": "通过", "warn": "待确认", "error": "待处理"}
        for row, check in enumerate(checks):
            for column, value in enumerate((check.title, names[check.state], check.detail + ("\n" + check.remedy if check.remedy else ""))):
                item = QTableWidgetItem(value)
                if column == 1:
                    item.setForeground(QColor(self.state_colors[check.state]))
                if column == 2:
                    item.setToolTip(value)
                self.table.setItem(row, column, item)
        self.table.resizeRowsToContents()
        for row in range(len(checks)):
            self.table.setRowHeight(row, max(72, self.table.rowHeight(row)))
        self.update_launch_buttons()
        self.append_activity(f"检查完成：{errors} 项需要处理，{warnings} 项待确认。")
        if self.load_error:
            self.append_activity(self.load_error)

    def prepare_config(self):
        if self.runtime.owned():
            self.failure("请先停止本次启动，再进行本机配置和数据库初始化。")
            return
        try:
            settings = self.form_settings()
        except LauncherError as exc:
            self.failure(str(exc))
            return
        answer = QMessageBox.question(self, "一键完成配置",
            f"将保存设置和密码，备份并更新不同的服务配置，自动选择数据库程序并准备运行环境，\n"
            f"并为本机数据库 {settings.dbname}（端口 {settings.dbport}）创建数据库及应用迁移。\n"
            "请确认这是你要使用的数据库。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        password = self.db_password.text()
        def done(lines):
            self.settings = settings
            self.load_error = ""
            self.append_activity("\n".join(lines))
            self.go(2)
            QTimer.singleShot(100, self.run_checks)
        self.go(2)
        self.run_job(lambda progress, password_saved: configure_all(settings, self.root, password=password,
                     progress=progress, on_password_saved=password_saved), done,
                     kind="configure", password_updates=True)

    def save_settings(self):
        try:
            settings = self.form_settings()
            ports_changed = settings.ports != self.settings.ports
            if self.runtime.owned() and settings.ports != (self.runtime.running_ports or self.settings.ports):
                raise LauncherError("请先停止本次启动，再修改端口。")
            self.save_password()
            if ports_changed:
                replace_server_config(settings, self.root)
            else:
                atomic_json(self.root / "runtime/settings.json", asdict(settings))
            self.settings = settings
            self.load_error = ""
            self.append_activity("已保存端口设置并更新服务配置，已有配置已另存备份。" if ports_changed else
                                 "已保存本机设置。服务配置未自动覆盖，请重新检查一致性。")
            self.run_checks()
        except (LauncherError, OSError) as exc:
            self.failure(str(exc) if isinstance(exc, LauncherError) else "设置保存失败，请检查目录写入权限。")

    def update_config(self):
        if self.runtime.owned():
            self.failure("请先停止本次启动，再更新服务配置。")
            return
        answer = QMessageBox.question(self, "更新服务配置", "将备份已有服务配置，并根据当前设置生成本地模式配置。是否继续？")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            settings = self.form_settings()
            self.save_password()
            replace_server_config(settings, self.root)
            self.settings = settings
            self.load_error = ""
            self.append_activity("服务配置已更新，已有文件已另存本机备份。")
            self.run_checks()
        except (LauncherError, OSError) as exc:
            self.failure(str(exc) if isinstance(exc, LauncherError) else "服务配置更新失败，请检查目录写入权限。")

    def start_game(self):
        try:
            settings = self.form_settings()
        except LauncherError as exc:
            self.failure(str(exc))
            return
        self.go(2)
        password = self.db_password.text()
        self.run_job(lambda progress: self.runtime.start(settings, progress, password=password),
                     lambda result: self.append_activity("启动流程完成。"), kind="start")

    def stop_game(self):
        self.run_job(lambda progress: self.runtime.stop(), lambda result: self.append_activity("已停止本次启动的进程。"), kind="stop")

    def closeEvent(self, event):
        if self.worker is not None:
            QMessageBox.information(self, "操作进行中", "请等待当前操作结束后再关闭。")
            event.ignore()
            return
        if self.runtime.owned():
            answer = QMessageBox.question(self, "退出启动器", "退出时将停止本次启动的游戏、本地接入和服务。是否继续？")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            event.ignore()
            self.run_job(lambda progress: self.runtime.stop(), lambda result: QTimer.singleShot(100, self.close), kind="stop")
            return
        self.status_timer.stop()
        if self.status_worker is not None and not self.status_worker.wait(1500):
            event.ignore()
            QTimer.singleShot(100, self.close)
            return
        event.accept()


def main():
    set_application_identity()
    app = QApplication(sys.argv)
    app.setApplicationName("MasterofGarden")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(application_icon())
    app.setFont(QFont("Microsoft YaHei UI", 10))
    (ROOT / "runtime").mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(ROOT / "runtime/launcher.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.information(None, "启动器已打开", "此项目的启动器已在运行。请使用已有窗口。")
        return 1
    window = LauncherWindow()
    window.show()
    return app.exec()
