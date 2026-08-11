import {
  FormEvent,
  useEffect,
  useMemo,
  useState
} from "react";

import {
  checkAllServerStatus,
  checkUpdates,
  cleanupServer,
  clearHistory,
  createServer,
  createTask,
  deleteServer,
  deleteTask,
  deleteDiscordNotificationSettings,
  deleteEmailNotificationSettings,
  discoverServer,
  getCredentialStatus,
  getHealth,
  getHistory,
  getNotificationSettings,
  getRebootStatus,
  getServers,
  getSettings,
  getTaskRun,
  getTaskRunHistory,
  getTaskRuns,
  getTasks,
  getUpdateSnapshot,
  installAllUpdates,
  installHeldUpdates,
  installSelectedUpdates,
  lockUpdatePackage,
  privilegeCheck,
  unlockUpdatePackage,
  runTaskNow,
  setServerCredentials,
  saveDiscordNotificationSettings,
  saveEmailNotificationSettings,
  saveNotificationEventPreferences,
  setDiscordNotificationEnabled,
  setEmailNotificationEnabled,
  testNotification,
  updateNotificationSettings,
  updateServer,
  updateSettings,
  updateTask
} from "./api";

import type {
  HistoryEntry,
  PackageUpdate,
  NotificationEventPreference,
  NotificationSettings,
  RebootStatus,
  ScheduledTask,
  Server,
  TaskRunDetail,
  TaskRunSummary,
  UpdateResult
} from "./types";


type Page =
  | "dashboard"
  | "servers"
  | "tasks"
  | "history"
  | "settings";


const GITHUB_URL =
  "https://github.com/Mauckisch/patchforge";


function formatDate(
  value: string | null
): string {
  if (!value) {
    return "Never";
  }

  const hasTimezone =
    /(?:Z|[+-]\\d{2}:?\\d{2})$/i.test(
      value
    );

  const date = new Date(
    hasTimezone
      ? value
      : `${value}Z`
  );

  if (Number.isNaN(date.getTime())) {
    return "Invalid date";
  }

  return new Intl.DateTimeFormat(
    undefined,
    {
      dateStyle: "short",
      timeStyle: "short"
    }
  ).format(date);
}


function formatTopbarDate(
  date: Date,
  timezone: string,
): string {
  try {
    const parts = new Intl.DateTimeFormat(
      "en-CA",
      {
        timeZone: timezone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }
    ).formatToParts(date);

    const values = Object.fromEntries(
      parts.map(
        (part) => [
          part.type,
          part.value
        ]
      )
    );

    return (
      `${values.year}-`
      + `${values.month}-`
      + `${values.day}`
    );

  } catch {
    const year = date.getFullYear();
    const month = String(
      date.getMonth() + 1
    ).padStart(2, "0");
    const day = String(
      date.getDate()
    ).padStart(2, "0");

    return `${year}-${month}-${day}`;
  }
}


function formatTopbarTime(
  date: Date,
  timezone: string,
): string {
  try {
    return new Intl.DateTimeFormat(
      undefined,
      {
        timeZone: timezone,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }
    ).format(date);

  } catch {
    return new Intl.DateTimeFormat(
      undefined,
      {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }
    ).format(date);
  }
}


function getTimezones(): string[] {
  try {
    return Intl.supportedValuesOf(
      "timeZone"
    );
  } catch {
    return [
      "UTC",
      "Europe/Berlin"
    ];
  }
}


function App() {
  const [page, setPage] =
    useState<Page>("dashboard");

  const [showAbout, setShowAbout] =
    useState(false);

  const [currentTime, setCurrentTime] =
    useState(() => new Date());

  const [appVersion, setAppVersion] =
    useState("unknown");

  const [servers, setServers] =
    useState<Server[]>([]);

  const [tasks, setTasks] =
    useState<ScheduledTask[]>([]);

  const [history, setHistory] =
    useState<HistoryEntry[]>([]);

  const [taskRunHistory, setTaskRunHistory] =
    useState<TaskRunSummary[]>([]);

  const [
    historyRetentionDays,
    setHistoryRetentionDays
  ] = useState<number | null>(7);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [deletingServer, setDeletingServer] =
    useState<Server | null>(null);

  const [showAddServer, setShowAddServer] =
    useState(false);

  const [updateServer, setUpdateServer] =
    useState<Server | null>(null);

  const [editingServer, setEditingServer] =
    useState<Server | null>(null);

  const [showAddTask, setShowAddTask] =
    useState(false);

  const [taskTimezone, setTaskTimezone] =
    useState<string>(() => {
      const saved = localStorage.getItem(
        "patchforge-task-timezone"
      );

      if (saved) {
        return saved;
      }

      return (
        Intl.DateTimeFormat()
          .resolvedOptions()
          .timeZone
        || "UTC"
      );
    });

  const [editingTask, setEditingTask] =
    useState<ScheduledTask | null>(null);


  async function loadData() {
    setLoading(true);
    setError(null);

    try {
      const [
        serverData,
        taskData,
        historyData,
        taskRunHistoryData,
        healthData
      ] = await Promise.all([
        getServers(),
        getTasks(),
        getHistory(),
        getTaskRunHistory(),
        getHealth()
      ]);

      setAppVersion(
        healthData.version
      );

      setServers(serverData);
      setTasks(taskData);
      setHistory(historyData);
      setTaskRunHistory(
        taskRunHistoryData
      );

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load PatchForge data"
      );

    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    void loadData();

    let cancelled = false;
    let statusTimer: number | undefined;

    async function pollServerStatus() {
      try {
        await checkAllServerStatus();

        const serverData =
          await getServers();

        if (!cancelled) {
          setServers(serverData);
        }

      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to check server status"
          );
        }
      }

      if (!cancelled) {
        statusTimer = window.setTimeout(
          () => {
            void pollServerStatus();
          },
          60000
        );
      }
    }

    void pollServerStatus();

    return () => {
      cancelled = true;

      if (statusTimer !== undefined) {
        window.clearTimeout(
          statusTimer
        );
      }
    };
  }, []);


  useEffect(() => {
    const timer = window.setInterval(
      () => {
        setCurrentTime(
          new Date()
        );
      },
      1000
    );

    return () => {
      window.clearInterval(timer);
    };
  }, []);


  const rebootCount = useMemo(
    () =>
      servers.filter(
        (server) =>
          server.reboot_required
      ).length,
    [servers]
  );


  const enabledTasks = useMemo(
    () =>
      tasks.filter(
        (task) =>
          task.enabled
      ).length,
    [tasks]
  );

  const onlineCount = useMemo(
    () =>
      servers.filter(
        (server) =>
          server.connection_status === "ONLINE"
      ).length,
    [servers]
  );

  const availableUpdates = useMemo(
    () =>
      servers.reduce(
        (total, server) =>
          total + server.updates_available,
        0
      ),
    [servers]
  );


  async function confirmDeleteServer() {
    if (!deletingServer) {
      return;
    }

    try {
      await deleteServer(
        deletingServer.id
      );

      setDeletingServer(null);

      await loadData();

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to delete server"
      );
    }
  }


  function pageTitle(): string {
    switch (page) {
      case "servers":
        return "Servers";

      case "tasks":
        return "Tasks";

      case "history":
        return "History";

      case "settings":
        return "Settings";

      default:
        return "Dashboard";
    }
  }


  return (
    <div className="layout">
      <header className="app-topbar">
        <div className="topbar-brand">
          <div className="brand-mark">
            <img
              src="/branding/patchforge-icon.svg"
              alt="PatchForge"
              className="brand-logo"
            />
          </div>

          <div>
            <div className="brand-title">
              PatchForge
            </div>

            <div className="brand-version">
              Linux Update Management
            </div>
          </div>
        </div>

        <div className="topbar-clock">
          <strong>
            {formatTopbarDate(
              currentTime,
              taskTimezone
            )}
            {" "}
            {formatTopbarTime(
              currentTime,
              taskTimezone
            )}
          </strong>

          <span>
            {taskTimezone}
          </span>
        </div>

        <div
          className="topbar-spacer"
          aria-hidden="true"
        />
      </header>

      <aside className="sidebar">
        <nav className="nav">
          {[
            ["dashboard", "Dashboard"],
            ["servers", "Servers"],
            ["tasks", "Tasks"],
            ["history", "History"],
            ["settings", "Settings"]
          ].map(([key, label]) => (
            <button
              key={key}
              className={
                `nav-button ${
                  page === key
                    ? "active"
                    : ""
                }`
              }
              onClick={() =>
                setPage(key as Page)
              }
            >
              {label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button
            type="button"
            className="sidebar-about"
            onClick={() =>
              setShowAbout(true)
            }
          >
            <span className="sidebar-about-icon">
              ⓘ
            </span>

            <span>
              PatchForge v{appVersion}
            </span>
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="page-header">
          <div>
            <h1 className="page-title">
              {pageTitle()}
            </h1>

            <p className="page-subtitle">
              Linux update management
            </p>
          </div>

        </header>

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}

        {loading ? (
          <div className="loading">
            Loading PatchForge…
          </div>
        ) : (
          <>
            {page === "dashboard" && (
              <Dashboard
                servers={servers}
                tasks={tasks}
                history={history}
                rebootCount={rebootCount}
                enabledTasks={enabledTasks}
                onlineCount={onlineCount}
                availableUpdates={availableUpdates}
                onRefreshStatus={async () => {
                  try {
                    await checkAllServerStatus();
                    await loadData();

                  } catch (err) {
                    setError(
                      err instanceof Error
                        ? err.message
                        : "Unable to check server status"
                    );
                  }
                }}
                onOpenServers={() =>
                  setPage("servers")
                }
              />
            )}

            {page === "servers" && (
              <ServerPanel
                servers={servers}
                onUpdates={setUpdateServer}
                onEdit={setEditingServer}
                onDelete={setDeletingServer}
                onAdd={() =>
                  setShowAddServer(true)
                }
              />
            )}

            {page === "tasks" && (
              <TasksPanel
                tasks={tasks}
                servers={servers}
                onAdd={() =>
                  setShowAddTask(true)
                }
                onChanged={loadData}
                onError={setError}
                onEdit={setEditingTask}
              />
            )}

            {page === "history" && (
              <HistoryPanel
                history={history}
                taskRuns={taskRunHistory}
                allowClear={true}
                retentionDays={historyRetentionDays}
                onRetentionChange={async (days) => {
                  try {
                    const result =
                      await updateSettings(days);

                    setHistoryRetentionDays(
                      result.history_retention_days
                    );

                    await loadData();

                  } catch (err) {
                    setError(
                      err instanceof Error
                        ? err.message
                        : "Unable to update history retention"
                    );
                  }
                }}
                onClear={async () => {
                  if (!window.confirm(
                    "Delete the complete PatchForge history? This cannot be undone."
                  )) {
                    return;
                  }

                  try {
                    await clearHistory();
                    await loadData();

                  } catch (err) {
                    setError(
                      err instanceof Error
                        ? err.message
                        : "Unable to clear history"
                    );
                  }
                }}
              />
            )}

          {page === "settings" && (
            <SettingsPanel
              taskTimezone={taskTimezone}
              onTaskTimezoneChange={(timezone) => {
                setTaskTimezone(timezone);

                localStorage.setItem(
                  "patchforge-task-timezone",
                  timezone
                );
              }}
            />
          )}
          </>
        )}
      </main>

      {showAbout && (
        <div
          className="modal-backdrop"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              setShowAbout(false);
            }
          }}
        >
          <div className="modal about-modal">
            <div className="about-header">
              <span>
                PatchForge
              </span>

              <button
                type="button"
                className="about-close"
                aria-label="Close"
                onClick={() =>
                  setShowAbout(false)
                }
              >
                ×
              </button>
            </div>

            <div className="about-product">
              <img
                src="/branding/patchforge-icon.svg"
                alt=""
                className="about-logo"
              />

              <div>
                <h2>
                  PatchForge
                </h2>

                <div className="about-version">
                  VERSION {appVersion}
                </div>

                <p>
                  Linux Update Management
                </p>
              </div>
            </div>

            <div className="about-grid">
              <div className="about-card">
                <span>
                  Frontend
                </span>

                <strong>
                  React + TypeScript
                </strong>
              </div>

              <div className="about-card">
                <span>
                  Backend
                </span>

                <strong>
                  FastAPI
                </strong>
              </div>

              <div className="about-card">
                <span>
                  Database
                </span>

                <strong>
                  SQLite
                </strong>
              </div>

              <div className="about-card">
                <span>
                  Project
                </span>

                <strong>
                  PatchForge for Linux
                </strong>
              </div>
            </div>

            <div className="about-copyright">
              <span>
                Copyright
              </span>

              <strong>
                © 2026 Dennis Mauckisch
              </strong>
            </div>

            <div className="about-actions">
              <a
                className="button"
                href={GITHUB_URL}
                target="_blank"
                rel="noreferrer"
              >
                GitHub
              </a>

              <button
                type="button"
                className="button primary"
                onClick={() =>
                  setShowAbout(false)
                }
              >
                Close
              </button>
            </div>

            <span
              className="about-a11y-marker"
              aria-hidden="true"
            >
              PatchForge About
            </span>
          </div>
        </div>
      )}

      {deletingServer && (
        <div className="modal-backdrop">
          <div className="modal">
            <h2>
              Delete server?
            </h2>

            <p>
              You are about to remove{" "}
              <strong>
                {deletingServer.name}
              </strong>
              .
            </p>

            <div className="modal-server">
              {deletingServer.host}
            </div>

            <p className="modal-note">
              Stored credentials, SSH host key and scheduled
              tasks for this server will be removed.
              History entries will be kept.
            </p>

            <div className="modal-actions">
              <button
                className="button"
                onClick={() =>
                  setDeletingServer(null)
                }
              >
                Cancel
              </button>

              <button
                className="button danger"
                onClick={() =>
                  void confirmDeleteServer()
                }
              >
                Delete Server
              </button>
            </div>
          </div>
        </div>
      )}

      {showAddServer && (
        <AddServerModal
          onClose={() =>
            setShowAddServer(false)
          }
          onCreated={async () => {
            setShowAddServer(false);
            await loadData();
          }}
        />
      )}

      {updateServer && (
        <UpdateModal
          server={updateServer}
          onClose={() =>
            setUpdateServer(null)
          }
          onChanged={loadData}
          onError={setError}
        />
      )}

      {editingServer && (
        <EditServerModal
          server={editingServer}
          onClose={() =>
            setEditingServer(null)
          }
          onSaved={async () => {
            setEditingServer(null);
            await loadData();
          }}
          onError={setError}
        />
      )}

      {showAddTask && (
        <AddTaskModal
          servers={servers}
          defaultTimezone={taskTimezone}
          onClose={() =>
            setShowAddTask(false)
          }
          onCreated={async () => {
            setShowAddTask(false);
            await loadData();
          }}
          onError={setError}
        />
      )}


      {editingTask && (
        <AddTaskModal
          servers={servers}
          task={editingTask}
          defaultTimezone={taskTimezone}
          onClose={() =>
            setEditingTask(null)
          }
          onCreated={async () => {
            setEditingTask(null);
            await loadData();
          }}
          onError={setError}
        />
      )}
    </div>
  );
}


function Dashboard({
  servers,
  history,
  rebootCount,
  enabledTasks,
  onlineCount,
  availableUpdates,
  onRefreshStatus,
  onOpenServers
}: {
  servers: Server[];
  tasks: ScheduledTask[];
  history: HistoryEntry[];
  rebootCount: number;
  enabledTasks: number;
  onlineCount: number;
  availableUpdates: number;
  onRefreshStatus: () => Promise<void>;
  onOpenServers: () => void;
}) {
  const [refreshing, setRefreshing] =
    useState(false);


  async function refreshStatus() {
    setRefreshing(true);

    try {
      await onRefreshStatus();

    } finally {
      setRefreshing(false);
    }
  }


  return (
    <>
      <section className="stats dashboard-stats">
        <div className="stat-card">
          <div className="stat-label">
            Servers
          </div>

          <div className="stat-value">
            {servers.length}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">
            Online
          </div>

          <div className="stat-value">
            {onlineCount}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">
            Updates available
          </div>

          <div
            className={
              `stat-value ${
                availableUpdates > 0
                  ? "warning"
                  : ""
              }`
            }
          >
            {availableUpdates}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">
            Reboot required
          </div>

          <div
            className={
              `stat-value ${
                rebootCount > 0
                  ? "warning"
                  : ""
              }`
            }
          >
            {rebootCount}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">
            Scheduled tasks
          </div>

          <div className="stat-value">
            {enabledTasks}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2 className="panel-title">
            Server Status
          </h2>

          <div className="dashboard-actions">
            <button
              className="button"
              disabled={refreshing}
              onClick={() =>
                void refreshStatus()
              }
            >
              {refreshing
                ? "Checking…"
                : "Refresh Status"}
            </button>

            <button
              className="button"
              onClick={onOpenServers}
            >
              Manage Servers
            </button>
          </div>
        </div>

        {servers.length === 0 ? (
          <div className="empty">
            No servers configured.
          </div>
        ) : (
          <div className="dashboard-server-list">
            {servers.map(
              (server) => (
                <div
                  className="dashboard-server-row dashboard-server-row-wide"
                  key={server.id}
                >
                  <div>
                    <strong>
                      {server.name}
                    </strong>

                    <div className="server-host">
                      {server.host}
                    </div>
                  </div>

                  <span
                    className={
                      server.connection_status === "ONLINE"
                        ? "badge ok"
                        : server.connection_status === "UNKNOWN"
                          ? "badge neutral"
                          : "badge danger"
                    }
                  >
                    {server.connection_status}
                  </span>

                  <div className="dashboard-number">
                    <strong>
                      {server.updates_available}
                    </strong>

                    <span>
                      updates
                    </span>
                  </div>

                  <span
                    className={
                      server.reboot_required
                        ? "badge warning"
                        : "badge ok"
                    }
                  >
                    {server.reboot_required
                      ? "Reboot required"
                      : "No reboot"}
                  </span>

                  <div className="dashboard-last-seen">
                    <span>
                      Last seen
                    </span>

                    <strong>
                      {formatDate(
                        server.last_seen_at
                      )}
                    </strong>
                  </div>
                </div>
              )
            )}
          </div>
        )}
      </section>

      <HistoryPanel
        history={history.slice(0, 5)}
      />
    </>
  );
}

function AddTaskModal({
  servers,
  task,
  defaultTimezone,
  onClose,
  onCreated,
  onError
}: {
  servers: Server[];
  task?: ScheduledTask;
  defaultTimezone: string;
  onClose: () => void;
  onCreated: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const editing = Boolean(task);

  const [name, setName] =
    useState(
      task?.name ?? ""
    );

  const [serverIds, setServerIds] =
    useState<number[]>(
      task?.server_ids
      ?? (
        servers.length
          ? [servers[0].id]
          : []
      )
    );

  const [action, setAction] =
    useState<
      "CHECK" |
      "INSTALL_ALL" |
      "CLEANUP" |
      "REBOOT_CHECK"
    >(
      (
        task?.action
        ?? "CHECK"
      ) as
        "CHECK" |
        "INSTALL_ALL" |
        "CLEANUP" |
        "REBOOT_CHECK"
    );

  const [scheduleType, setScheduleType] =
    useState<
      "once" |
      "daily" |
      "weekly" |
      "monthly"
    >(
      (
        task?.schedule_type
        ?? "daily"
      ) as
        "once" |
        "daily" |
        "weekly" |
        "monthly"
    );

  const timezones = useMemo(
    () =>
      getTimezones(),
    []
  );

  const [timezone, setTimezone] =
    useState(
      task?.timezone
      ?? defaultTimezone
    );

  const [hour, setHour] =
    useState(
      task?.hour ?? 3
    );

  const [minute, setMinute] =
    useState(
      task?.minute ?? 0
    );

  const [weekday, setWeekday] =
    useState(
      task?.weekday ?? 0
    );

  const [dayOfMonth, setDayOfMonth] =
    useState(
      task?.day_of_month ?? 1
    );

  const [runAt, setRunAt] =
    useState(
      task?.run_at
        ? task.run_at.slice(0, 16)
        : ""
    );

  const [enabled, setEnabled] =
    useState(
      task?.enabled ?? true
    );

  const [
    notifyOnlyOnUpdates,
    setNotifyOnlyOnUpdates
  ] = useState(
    task?.notify_only_on_updates ?? false
  );

  const [saving, setSaving] =
    useState(false);


  function toggleServer(
    serverId: number
  ) {
    setServerIds(
      (current) =>
        current.includes(serverId)
          ? current.filter(
              (id) =>
                id !== serverId
            )
          : [
              ...current,
              serverId
            ]
    );
  }


  async function submit(
    event: FormEvent
  ) {
    event.preventDefault();

    if (serverIds.length === 0) {
      onError(
        "Select at least one target server"
      );
      return;
    }

    setSaving(true);

    try {
      const payload = {
        name,
        server_ids: serverIds,
        action,
        schedule_type: scheduleType,
        timezone,
        enabled,
        notify_only_on_updates:
          action === "CHECK"
            ? notifyOnlyOnUpdates
            : false,
        ...(scheduleType === "once"
          ? {
              run_at: runAt
            }
          : {
              hour,
              minute
            }),
        ...(scheduleType === "weekly"
          ? {
              weekday
            }
          : {}),
        ...(scheduleType === "monthly"
          ? {
              day_of_month: dayOfMonth
            }
          : {})
      };

      if (task) {
        await updateTask(
          task.id,
          payload
        );

      } else {
        await createTask(
          payload
        );
      }

      await onCreated();

    } catch (err) {
      onError(
        err instanceof Error
          ? err.message
          : (
              editing
                ? "Unable to update task"
                : "Unable to create task"
            )
      );

    } finally {
      setSaving(false);
    }
  }


  return (
    <div className="modal-backdrop">
      <div className="modal modal-large">
        <h2>
          {editing
            ? "Edit Task"
            : "Add Task"}
        </h2>

        <form
          className="form-grid"
          onSubmit={(event) =>
            void submit(event)
          }
        >
          <label className="form-full">
            <span>Name</span>

            <input
              required
              value={name}
              onChange={(event) =>
                setName(
                  event.target.value
                )
              }
            />
          </label>

          <div className="form-full">
            <span className="form-section-label">
              Target Servers
            </span>

            <div className="target-list">
              <label className="target-select-all">
                <input
                  type="checkbox"
                  checked={
                    servers.length > 0 &&
                    serverIds.length === servers.length
                  }
                  onChange={(event) =>
                    setServerIds(
                      event.target.checked
                        ? servers.map(
                            (server) =>
                              server.id
                          )
                        : []
                    )
                  }
                />

                <strong>
                  Select All
                </strong>
              </label>

              {servers.map(
                (server) => (
                  <label
                    className="target-item"
                    key={server.id}
                  >
                    <input
                      type="checkbox"
                      checked={
                        serverIds.includes(
                          server.id
                        )
                      }
                      onChange={() =>
                        toggleServer(
                          server.id
                        )
                      }
                    />

                    <div>
                      <strong>
                        {server.name}
                      </strong>

                      <div className="server-host">
                        {server.host}
                      </div>
                    </div>
                  </label>
                )
              )}
            </div>
          </div>

          <label>
            <span>Action</span>

            <select
              value={action}
              onChange={(event) =>
                setAction(
                  event.target.value as
                    "CHECK" |
                    "INSTALL_ALL" |
                    "CLEANUP" |
                    "REBOOT_CHECK"
                )
              }
            >
              <option value="CHECK">
                Check Updates
              </option>

              <option value="INSTALL_ALL">
                Install All Updates
              </option>

              <option value="CLEANUP">
                Cleanup
              </option>

              <option value="REBOOT_CHECK">
                Check Reboot Status
              </option>
            </select>
          </label>

          <label>
            <span>Schedule</span>

            <select
              value={scheduleType}
              onChange={(event) =>
                setScheduleType(
                  event.target.value as
                    "once" |
                    "daily" |
                    "weekly" |
                    "monthly"
                )
              }
            >
              <option value="once">
                Once
              </option>

              <option value="daily">
                Daily
              </option>

              <option value="weekly">
                Weekly
              </option>

              <option value="monthly">
                Monthly
              </option>
            </select>
          </label>

          <label className="form-full">
            <span>Timezone (override)</span>

            <select
              value={timezone}
              onChange={(event) =>
                setTimezone(
                  event.target.value
                )
              }
            >
              {timezones.map(
                (zone) => (
                  <option
                    key={zone}
                    value={zone}
                  >
                    {zone}
                  </option>
                )
              )}
            </select>
          </label>

          {scheduleType === "once" && (
            <label className="form-full">
              <span>Run At</span>

              <input
                required
                type="datetime-local"
                value={runAt}
                onChange={(event) =>
                  setRunAt(
                    event.target.value
                  )
                }
              />
            </label>
          )}

          {scheduleType !== "once" && (
            <>
              <label>
                <span>Hour</span>

                <input
                  required
                  type="number"
                  min="0"
                  max="23"
                  value={hour}
                  onChange={(event) =>
                    setHour(
                      Number(
                        event.target.value
                      )
                    )
                  }
                />
              </label>

              <label>
                <span>Minute</span>

                <input
                  required
                  type="number"
                  min="0"
                  max="59"
                  value={minute}
                  onChange={(event) =>
                    setMinute(
                      Number(
                        event.target.value
                      )
                    )
                  }
                />
              </label>
            </>
          )}

          {scheduleType === "weekly" && (
            <label className="form-full">
              <span>Weekday</span>

              <select
                value={weekday}
                onChange={(event) =>
                  setWeekday(
                    Number(
                      event.target.value
                    )
                  )
                }
              >
                <option value="0">Monday</option>
                <option value="1">Tuesday</option>
                <option value="2">Wednesday</option>
                <option value="3">Thursday</option>
                <option value="4">Friday</option>
                <option value="5">Saturday</option>
                <option value="6">Sunday</option>
              </select>
            </label>
          )}

          {scheduleType === "monthly" && (
            <label className="form-full">
              <span>
                Day of Month
              </span>

              <input
                required
                type="number"
                min="1"
                max="31"
                value={dayOfMonth}
                onChange={(event) =>
                  setDayOfMonth(
                    Number(
                      event.target.value
                    )
                  )
                }
              />
            </label>
          )}

          <label className="checkbox-label form-full">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(event) =>
                setEnabled(
                  event.target.checked
                )
              }
            />

            <span>
              Task enabled
            </span>
          </label>

          {action === "CHECK" && (
            <label className="checkbox-label form-full">
              <input
                type="checkbox"
                checked={notifyOnlyOnUpdates}
                onChange={(event) =>
                  setNotifyOnlyOnUpdates(
                    event.target.checked
                  )
                }
              />

              <span>
                Notify only when updates are found
              </span>
            </label>
          )}

          {action === "INSTALL_ALL" && (
            <div className="task-warning form-full">
              This task installs all available updates
              automatically on all selected target servers.
            </div>
          )}

          <div className="modal-actions form-full">
            <button
              type="button"
              className="button"
              disabled={saving}
              onClick={onClose}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="button primary"
              disabled={
                saving ||
                serverIds.length === 0
              }
            >
              {saving
                ? "Saving…"
                : (
                    editing
                      ? "Save Changes"
                      : "Create Task"
                  )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function TasksPanel({
  tasks,
  servers,
  onAdd,
  onChanged,
  onError,
  onEdit
}: {
  tasks: ScheduledTask[];
  servers: Server[];
  onAdd: () => void;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onEdit: (task: ScheduledTask) => void;
}) {
  const [busyTask, setBusyTask] =
    useState<number | null>(null);

  const [runTask, setRunTask] =
    useState<ScheduledTask | null>(null);

  const [taskRuns, setTaskRuns] =
    useState<TaskRunSummary[]>([]);

  const [selectedRun, setSelectedRun] =
    useState<TaskRunDetail | null>(null);

  const [loadingRuns, setLoadingRuns] =
    useState(false);


  async function openRuns(
    task: ScheduledTask
  ) {
    setRunTask(task);
    setSelectedRun(null);
    setLoadingRuns(true);

    try {
      const runs = await getTaskRuns(
        task.id
      );

      setTaskRuns(runs);

    } catch (err) {
      onError(
        err instanceof Error
          ? err.message
          : "Unable to load task runs"
      );

    } finally {
      setLoadingRuns(false);
    }
  }


  async function openRunDetail(
    taskId: number,
    runId: number
  ) {
    setLoadingRuns(true);

    try {
      const detail = await getTaskRun(
        taskId,
        runId
      );

      setSelectedRun(detail);

    } catch (err) {
      onError(
        err instanceof Error
          ? err.message
          : "Unable to load task run details"
      );

    } finally {
      setLoadingRuns(false);
    }
  }


  async function toggleTask(
    task: ScheduledTask
  ) {
    setBusyTask(task.id);

    try {
      await updateTask(
        task.id,
        {
          name: task.name,
          server_ids: task.server_ids,
          action: task.action as
            "CHECK" |
            "INSTALL_ALL" |
            "CLEANUP" |
            "REBOOT_CHECK",
          schedule_type: task.schedule_type as
            "once" |
            "daily" |
            "weekly" |
            "monthly",
          timezone: task.timezone,
          enabled: !task.enabled,
          notify_only_on_updates:
            task.notify_only_on_updates,

          ...(task.schedule_type === "once"
            ? {
                run_at: task.run_at ?? undefined
              }
            : {
                hour: task.hour ?? 0,
                minute: task.minute ?? 0
              }),

          ...(task.schedule_type === "weekly"
            ? {
                weekday: task.weekday ?? 0
              }
            : {}),

          ...(task.schedule_type === "monthly"
            ? {
                day_of_month: task.day_of_month ?? 1
              }
            : {})
        }
      );

      await onChanged();

    } catch (err) {
      onError(
        err instanceof Error
          ? err.message
          : "Unable to update task"
      );

    } finally {
      setBusyTask(null);
    }
  }


  async function runNow(
    task: ScheduledTask
  ) {
    if (!window.confirm(
      `Run task "${task.name}" now on ${task.server_ids.length} target(s)?`
    )) {
      return;
    }

    setBusyTask(task.id);

    try {
      await runTaskNow(
        task.id
      );

      await onChanged();

    } catch (err) {
      onError(
        err instanceof Error
          ? err.message
          : "Unable to run task"
      );

    } finally {
      setBusyTask(null);
    }
  }


  async function removeTask(
    task: ScheduledTask
  ) {
    if (!window.confirm(
      `Delete task "${task.name}"?`
    )) {
      return;
    }

    setBusyTask(task.id);

    try {
      await deleteTask(
        task.id
      );

      await onChanged();

    } catch (err) {
      onError(
        err instanceof Error
          ? err.message
          : "Unable to delete task"
      );

    } finally {
      setBusyTask(null);
    }
  }


  return (
    <section className="panel">
      <div className="panel-header">
        <h2 className="panel-title">
          Scheduled Tasks
        </h2>

        <div className="task-header-actions">

          <button
            className="button primary"
            disabled={servers.length === 0}
            onClick={onAdd}
          >
            + Add Task
          </button>
        </div>
      </div>

      {tasks.length === 0 ? (
        <div className="empty">
          No scheduled tasks.
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Targets</th>
                <th>Action</th>
                <th>Schedule</th>
                <th>Timezone</th>
                <th>Last Run</th>
                <th>Next Run</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {tasks.map(
                (task) => (
                  <tr key={task.id}>
                    <td>
                      <strong>
                        {task.name}
                      </strong>
                    </td>

                    <td className="task-targets-cell">
                      <div className="task-targets">
                        {task.server_ids.map(
                          (serverId) => (
                            <div
                              key={serverId}
                              className="task-target"
                            >
                              {servers.find(
                                (server) =>
                                  server.id === serverId
                              )?.name ?? `Server ${serverId}`}
                            </div>
                          )
                        )}
                      </div>
                    </td>

                    <td>
                      {task.action}
                    </td>

                    <td>
                      {task.schedule_type}
                    </td>

                    <td>
                      {task.timezone}
                    </td>

                    <td>
                      {formatDate(
                        task.last_run_at
                      )}
                    </td>

                    <td>
                      {formatDate(
                        task.next_run_at
                      )}
                    </td>

                    <td>
                      <span
                        className={
                          task.enabled
                            ? "badge ok"
                            : "badge warning"
                        }
                      >
                        {task.enabled
                          ? "Enabled"
                          : "Disabled"}
                      </span>
                    </td>

                    <td>
                      <div className="table-actions">
                        <button
                          className="button small"
                          disabled={
                            busyTask === task.id
                          }
                          onClick={() =>
                            void openRuns(task)
                          }
                        >
                          Runs
                        </button>

                        <button
                          className="button small"
                          disabled={
                            busyTask === task.id
                          }
                          onClick={() =>
                            onEdit(task)
                          }
                        >
                          Edit
                        </button>

                        <button
                          className="button small"
                          disabled={
                            busyTask === task.id
                          }
                          onClick={() =>
                            void runNow(task)
                          }
                        >
                          Run Now
                        </button>

                        <button
                          className="button small"
                          disabled={
                            busyTask === task.id
                          }
                          onClick={() =>
                            void toggleTask(task)
                          }
                        >
                          {task.enabled
                            ? "Disable"
                            : "Enable"}
                        </button>

                        <button
                          className="button danger small"
                          disabled={
                            busyTask === task.id
                          }
                          onClick={() =>
                            void removeTask(task)
                          }
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        </div>
      )}
      {runTask && (
        <div className="modal-backdrop">
          <div className="modal modal-update">
            <div className="update-header">
              <div>
                <h2>
                  {runTask.name}
                </h2>

                <div className="server-host">
                  Task Runs · {runTask.action}
                </div>
              </div>

              <button
                type="button"
                className="button"
                onClick={() => {
                  setRunTask(null);
                  setSelectedRun(null);
                  setTaskRuns([]);
                }}
              >
                Close
              </button>
            </div>

            {loadingRuns ? (
              <div className="loading">
                Loading task runs…
              </div>

            ) : selectedRun ? (
              <>
                <div className="update-summary">
                  <div>
                    <span>Status</span>
                    <strong>
                      {selectedRun.status}
                    </strong>
                  </div>

                  <div>
                    <span>Successful</span>
                    <strong>
                      {selectedRun.success_count}
                    </strong>
                  </div>

                  <div>
                    <span>Failed</span>
                    <strong>
                      {selectedRun.failed_count}
                    </strong>
                  </div>
                </div>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Server</th>
                        <th>Status</th>
                        <th>Result</th>
                        <th>Reboot</th>
                      </tr>
                    </thead>

                    <tbody>
                      {selectedRun.results.map(
                        (result) => (
                          <tr key={result.id}>
                            <td>
                              <strong>
                                {result.server_name}
                              </strong>

                              <div className="server-host">
                                {result.host}
                              </div>
                            </td>

                            <td>
                              <span
                                className={
                                  result.status === "SUCCESS"
                                    ? "badge ok"
                                    : "badge danger"
                                }
                              >
                                {result.status}
                              </span>
                            </td>

                            <td>
                              {selectedRun.action === "CHECK" && (
                                <>
                                  <strong>
                                    {result.update_count} update(s)
                                  </strong>

                                  {result.updates.length > 0 && (
                                    <div className="task-run-packages">
                                      {result.updates.map(
                                        (pkg) => (
                                          <div key={pkg}>
                                            {pkg}
                                          </div>
                                        )
                                      )}
                                    </div>
                                  )}
                                </>
                              )}

                              {selectedRun.action === "INSTALL_ALL" && (
                                <>
                                  <strong>
                                    {result.installed_count} installed
                                  </strong>

                                  {result.installed_packages.length > 0 && (
                                    <div className="task-run-packages">
                                      {result.installed_packages.map(
                                        (pkg) => (
                                          <div key={pkg}>
                                            {pkg}
                                          </div>
                                        )
                                      )}
                                    </div>
                                  )}

                                  <div className="server-host">
                                    Remaining updates:{" "}
                                    {result.remaining_updates}
                                  </div>
                                </>
                              )}

                              {selectedRun.action === "CLEANUP" && (
                                <span>
                                  Cleanup completed
                                </span>
                              )}

                              {selectedRun.action === "REBOOT_CHECK" && (
                                <span>
                                  Reboot status checked
                                </span>
                              )}

                              {result.error && (
                                <div className="task-run-error">
                                  {result.error}
                                </div>
                              )}
                            </td>

                            <td>
                              <span
                                className={
                                  result.reboot_required
                                    ? "badge warning"
                                    : "badge ok"
                                }
                              >
                                {result.reboot_required
                                  ? "Required"
                                  : "No"}
                              </span>
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="modal-actions">
                  <button
                    type="button"
                    className="button"
                    onClick={() =>
                      setSelectedRun(null)
                    }
                  >
                    Back to Runs
                  </button>
                </div>
              </>

            ) : taskRuns.length === 0 ? (
              <div className="empty">
                No task runs recorded yet.
              </div>

            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Started</th>
                      <th>Status</th>
                      <th>Targets</th>
                      <th>Success</th>
                      <th>Failed</th>
                      <th>Updates</th>
                      <th></th>
                    </tr>
                  </thead>

                  <tbody>
                    {taskRuns.map(
                      (run) => (
                        <tr key={run.id}>
                          <td>
                            {formatDate(
                              run.started_at
                            )}
                          </td>

                          <td>
                            <span
                              className={
                                run.status === "SUCCESS"
                                  ? "badge ok"
                                  : (
                                      run.status === "PARTIAL"
                                        ? "badge warning"
                                        : "badge danger"
                                    )
                              }
                            >
                              {run.status}
                            </span>
                          </td>

                          <td>
                            {run.target_count}
                          </td>

                          <td>
                            {run.success_count}
                          </td>

                          <td>
                            {run.failed_count}
                          </td>

                          <td>
                            {run.updates_found}
                          </td>

                          <td>
                            <button
                              type="button"
                              className="button small"
                              onClick={() =>
                                void openRunDetail(
                                  run.task_id,
                                  run.id
                                )
                              }
                            >
                              Details
                            </button>
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

    </section>
  );
}


function EditServerModal({
  server,
  onClose,
  onSaved,
  onError
}: {
  server: Server;
  onClose: () => void;
  onSaved: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [name, setName] =
    useState(server.name);

  const [host, setHost] =
    useState(server.host);

  const [sshPort, setSshPort] =
    useState(server.ssh_port);

  const [username, setUsername] =
    useState(server.username);


  const [sshPassword, setSshPassword] =
    useState("");

  const [privilegePassword, setPrivilegePassword] =
    useState("");

  const [privilegeMethod, setPrivilegeMethod] =
    useState<
      "auto" |
      "sudo" |
      "su" |
      "none"
    >("auto");

  const [
    useSeparatePrivilegePassword,
    setUseSeparatePrivilegePassword
  ] = useState(false);

  const [credentialLoaded, setCredentialLoaded] =
    useState(false);

  const [saving, setSaving] =
    useState(false);

  const [statusText, setStatusText] =
    useState("");


  useEffect(() => {
    let active = true;

    getCredentialStatus(
      server.id
    )
      .then((status) => {
        if (!active) {
          return;
        }

        setPrivilegeMethod(
          status.privilege_method
        );

        setUseSeparatePrivilegePassword(
          status.separate_privilege_password
        );

        setCredentialLoaded(true);
      })
      .catch((err) => {
        if (!active) {
          return;
        }

        onError(
          err instanceof Error
            ? err.message
            : "Unable to load credential configuration"
        );

        setCredentialLoaded(true);
      });

    return () => {
      active = false;
    };
  }, [server.id]);


  async function submit(
    event: FormEvent
  ) {
    event.preventDefault();

    setSaving(true);

    try {
      const connectionChanged =
        host !== server.host
        || sshPort !== server.ssh_port
        || username !== server.username;

      const credentialChangeRequested =
        sshPassword.length > 0
        || privilegePassword.length > 0;

      setStatusText(
        "Saving server configuration…"
      );

      await updateServer(
        server.id,
        {
          name,
          host,
          ssh_port: sshPort,
          username
        }
      );

      if (credentialChangeRequested) {
        if (!sshPassword) {
          throw new Error(
            "Enter the SSH password when changing credentials."
          );
        }

        setStatusText(
          "Updating credentials…"
        );

        await setServerCredentials(
          server.id,
          {
            ssh_password: sshPassword,
            privilege_method: privilegeMethod,

            privilege_password:
              useSeparatePrivilegePassword
                ? privilegePassword
                : undefined
          }
        );
      }

      if (
        connectionChanged
        || credentialChangeRequested
      ) {
        setStatusText(
          "Running discovery…"
        );

        await discoverServer(
          server.id
        );

        setStatusText(
          "Checking privileges…"
        );

        await privilegeCheck(
          server.id
        );
      }

      setStatusText(
        "Server configuration saved."
      );

      await onSaved();

    } catch (err) {
      onError(
        err instanceof Error
          ? err.message
          : "Unable to update server"
      );

      setStatusText("");

    } finally {
      setSaving(false);
    }
  }


  return (
    <div className="modal-backdrop">
      <div className="modal modal-large">
        <h2>
          Edit Server
        </h2>

        <form
          className="form-grid"
          onSubmit={(event) =>
            void submit(event)
          }
        >
          <label>
            <span>Name</span>

            <input
              required
              value={name}
              onChange={(event) =>
                setName(
                  event.target.value
                )
              }
            />
          </label>

          <label>
            <span>Host / IP</span>

            <input
              required
              value={host}
              onChange={(event) =>
                setHost(
                  event.target.value
                )
              }
            />
          </label>

          <label>
            <span>SSH Port</span>

            <input
              required
              type="number"
              min="1"
              max="65535"
              value={sshPort}
              onChange={(event) =>
                setSshPort(
                  Number(
                    event.target.value
                  )
                )
              }
            />
          </label>

          <label>
            <span>Username</span>

            <input
              required
              value={username}
              onChange={(event) =>
                setUsername(
                  event.target.value
                )
              }
            />
          </label>



          <div className="edit-divider form-full">
            Credentials
          </div>

          <div className="form-help form-full">
            Leave password fields empty to keep the currently
            stored credentials.
          </div>

          <label className="form-full">
            <span>
              New SSH Password
            </span>

            <input
              type="password"
              autoComplete="new-password"
              value={sshPassword}
              onChange={(event) =>
                setSshPassword(
                  event.target.value
                )
              }
              placeholder="Leave empty to keep current password"
            />
          </label>

          <label>
            <span>
              Privilege Method
            </span>

            <select
              disabled={!credentialLoaded}
              value={privilegeMethod}
              onChange={(event) =>
                setPrivilegeMethod(
                  event.target.value as
                    "auto" |
                    "sudo" |
                    "su" |
                    "none"
                )
              }
            >
              <option value="auto">
                Automatic
              </option>

              <option value="sudo">
                sudo
              </option>

              <option value="su">
                su
              </option>

              <option value="none">
                None
              </option>
            </select>
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              disabled={!credentialLoaded}
              checked={
                useSeparatePrivilegePassword
              }
              onChange={(event) =>
                setUseSeparatePrivilegePassword(
                  event.target.checked
                )
              }
            />

            <span>
              Use separate privilege password
            </span>
          </label>

          {useSeparatePrivilegePassword && (
            <label className="form-full">
              <span>
                New Privilege Password
              </span>

              <input
                type="password"
                autoComplete="new-password"
                value={privilegePassword}
                onChange={(event) =>
                  setPrivilegePassword(
                    event.target.value
                  )
                }
                placeholder="Only required when changing credentials"
              />
            </label>
          )}

          {statusText && (
            <div className="form-status form-full">
              {statusText}
            </div>
          )}

          <div className="modal-actions form-full">
            <button
              type="button"
              className="button"
              disabled={saving}
              onClick={onClose}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="button primary"
              disabled={
                saving ||
                !credentialLoaded
              }
            >
              {saving
                ? "Saving…"
                : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


function AddServerModal({
  onClose,
  onCreated
}: {
  onClose: () => void;
  onCreated: () => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [host, setHost] = useState("");
  const [sshPort, setSshPort] = useState(22);
  const [username, setUsername] = useState("");
  const [sshPassword, setSshPassword] = useState("");

  const [privilegeMethod, setPrivilegeMethod] =
    useState<"auto" | "sudo" | "su" | "none">("auto");

  const [
    useSeparatePrivilegePassword,
    setUseSeparatePrivilegePassword
  ] = useState(false);

  const [
    privilegePassword,
    setPrivilegePassword
  ] = useState("");

  const [saving, setSaving] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);


  async function submit(
    event: FormEvent
  ) {
    event.preventDefault();

    setError(null);
    setSaving(true);

    let createdServer: Server | null = null;

    try {
      createdServer = await createServer({
        name,
        host,
        ssh_port: sshPort,
        username
      });

      await setServerCredentials(
        createdServer.id,
        {
          ssh_password: sshPassword,
          privilege_method: privilegeMethod,
          privilege_password:
            useSeparatePrivilegePassword
              ? privilegePassword
              : undefined
        }
      );

      await discoverServer(
        createdServer.id
      );

      await privilegeCheck(
        createdServer.id
      );

      await onCreated();

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to add server"
      );

      if (createdServer) {
        try {
          await deleteServer(
            createdServer.id
          );
        } catch {
          // Best-effort rollback.
        }
      }

    } finally {
      setSaving(false);
    }
  }


  return (
    <div className="modal-backdrop">
      <div className="modal modal-large">
        <h2>Add Server</h2>

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}

        <form
          className="form-grid"
          onSubmit={(event) =>
            void submit(event)
          }
        >
          <label>
            <span>Name</span>
            <input
              required
              value={name}
              onChange={(event) =>
                setName(event.target.value)
              }
            />
          </label>

          <label>
            <span>Host / IP</span>
            <input
              required
              value={host}
              onChange={(event) =>
                setHost(event.target.value)
              }
            />
          </label>

          <label>
            <span>SSH Port</span>
            <input
              required
              type="number"
              min="1"
              max="65535"
              value={sshPort}
              onChange={(event) =>
                setSshPort(
                  Number(
                    event.target.value
                  )
                )
              }
            />
          </label>

          <label>
            <span>Username</span>
            <input
              required
              value={username}
              onChange={(event) =>
                setUsername(event.target.value)
              }
            />
          </label>

          <label className="form-full">
            <span>SSH Password</span>
            <input
              required
              type="password"
              value={sshPassword}
              onChange={(event) =>
                setSshPassword(
                  event.target.value
                )
              }
            />
          </label>

          <label>
            <span>Privilege Method</span>

            <select
              value={privilegeMethod}
              onChange={(event) =>
                setPrivilegeMethod(
                  event.target.value as
                    "auto" |
                    "sudo" |
                    "su" |
                    "none"
                )
              }
            >
              <option value="auto">
                Automatic
              </option>

              <option value="sudo">
                sudo
              </option>

              <option value="su">
                su
              </option>

              <option value="none">
                None
              </option>
            </select>
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={
                useSeparatePrivilegePassword
              }
              onChange={(event) =>
                setUseSeparatePrivilegePassword(
                  event.target.checked
                )
              }
            />

            <span>
              Use separate privilege password
            </span>
          </label>

          {useSeparatePrivilegePassword && (
            <label className="form-full">
              <span>
                Privilege Password
              </span>

              <input
                required
                type="password"
                value={privilegePassword}
                onChange={(event) =>
                  setPrivilegePassword(
                    event.target.value
                  )
                }
              />
            </label>
          )}

          <div className="modal-actions form-full">
            <button
              type="button"
              className="button"
              disabled={saving}
              onClick={onClose}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="button primary"
              disabled={saving}
            >
              {saving
                ? "Adding…"
                : "Add Server"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


function UpdateModal({
  server,
  onClose,
  onChanged,
  onError
}: {
  server: Server;
  onClose: () => void;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [result, setResult] =
    useState<UpdateResult | null>(null);

  const [rebootStatus, setRebootStatus] =
    useState<RebootStatus | null>(null);

  const [selected, setSelected] =
    useState<string[]>([]);

  const [heldUpdates, setHeldUpdates] =
    useState<PackageUpdate[]>([]);

  const [selectedHeld, setSelectedHeld] =
    useState<string[]>([]);

  const [showHeldUpdates, setShowHeldUpdates] =
    useState(false);

  const [busy, setBusy] =
    useState(false);

  const [operationStatus, setOperationStatus] =
    useState<string | null>(null);

  const [snapshotLoaded, setSnapshotLoaded] =
    useState(false);

  const [updatesCheckedAt, setUpdatesCheckedAt] =
    useState<string | null>(
      server.updates_checked_at
    );


  async function loadSnapshot() {
    try {
      const snapshot =
        await getUpdateSnapshot(
          server.id
        );

      setResult({
        server_ids: [
          snapshot.server_id
        ],
        server:
          snapshot.server,
        system_hostname:
          snapshot.system_hostname,
        package_manager:
          snapshot.package_manager
          ?? server.package_manager
          ?? "unknown",
        updates_available:
          snapshot.updates_available,
        reboot_required:
          snapshot.reboot_required,
        cleanup_available:
          server.cleanup_available ?? undefined,
        updates:
          snapshot.updates
      });

      setHeldUpdates(
        snapshot.held_updates
      );

      setSelected(
        snapshot.updates
          .filter(
            (update) =>
              !update.locked
          )
          .map(
            (update) =>
              update.name
          )
      );

      setUpdatesCheckedAt(
        snapshot.updates_checked_at
      );

    } catch (err) {
      onError(
        err instanceof Error
          ? err.message
          : "Unable to load saved update status"
      );

    } finally {
      setSnapshotLoaded(true);
    }
  }


  async function togglePackageLock(
    update: PackageUpdate
  ) {
    setBusy(true);

    try {
      if (update.locked) {
        await unlockUpdatePackage(
          server.id,
          update.name
        );
      } else {
        await lockUpdatePackage(
          server.id,
          update.name
        );
      }

      setSelected(
        (current) =>
          current.filter(
            (packageName) =>
              packageName !== update.name
          )
      );

      setSelectedHeld(
        (current) =>
          current.filter(
            (packageName) =>
              packageName !== update.name
          )
      );

      await loadSnapshot();
      await onChanged();

    } catch (err) {
      onError(
        err instanceof Error
          ? err.message
          : "Unable to change package lock"
      );

    } finally {
      setBusy(false);
    }
  }


  async function refresh(
    statusMessage = "Checking for updates…"
  ) {
    setBusy(true);
    setOperationStatus(statusMessage);

    try {
      const [
        updateResult,
        rebootResult
      ] = await Promise.all([
        checkUpdates(server.id),
        getRebootStatus(server.id)
      ]);

      setResult(updateResult);
      setRebootStatus(rebootResult);

      setHeldUpdates(
        updateResult.held_updates ?? []
      );

      setSelectedHeld([]);

      setUpdatesCheckedAt(
        new Date().toISOString()
      );

      setSelected(
        updateResult.updates
          .filter(
            (update) =>
              !update.locked
          )
          .map(
            (update) =>
              update.name
          )
      );

      await onChanged();

    } catch (err) {
      onError(
        err instanceof Error
          ? err.message
          : "Update check failed"
      );

    } finally {
      setBusy(false);
      setOperationStatus(null);
    }
  }


  useEffect(() => {
    void loadSnapshot();
  }, [server.id]);


  return (
    <div className="modal-backdrop">
      <div className="modal modal-update">
        <div className="update-header">
          <div>
            <h2>{server.name}</h2>

            <div className="server-host">
              {server.host}
            </div>
          </div>

          <button
            className="button"
            disabled={busy}
            onClick={onClose}
          >
            Close
          </button>
        </div>

        <div className="update-summary">
          <div>
            <span>Updates</span>

            <strong>
              {result?.updates_available
                ?? server.updates_available}
            </strong>
          </div>

          <div>
            <span>Package Manager</span>

            <strong>
              {server.package_manager?.toUpperCase()
                ?? "Unknown"}
            </strong>
          </div>

          <div>
            <span>Reboot</span>

            <strong
              className={
                (
                  rebootStatus?.reboot_required
                  ?? server.reboot_required
                )
                  ? "text-warning"
                  : "text-ok"
              }
            >
              {(
                rebootStatus?.reboot_required
                ?? server.reboot_required
              )
                ? "Required"
                : "No"}
            </strong>
          </div>
        </div>

        <div className="update-last-checked">
          Last checked:{" "}
          <strong>
            {updatesCheckedAt
              ? formatDate(updatesCheckedAt)
              : "Never"}
          </strong>
        </div>

        {rebootStatus?.reboot_required && (
          <div className="reboot-warning">
            <strong>
              Reboot required
            </strong>

            <div className="reboot-reasons">
              {rebootStatus.reasons.map(
                (reason, index) => (
                  <div
                    className="reboot-reason"
                    key={`${reason.type}-${index}`}
                  >
                    <div>
                      {reason.message}
                    </div>

                    {reason.type === "kernel" && (
                      <div className="reboot-kernel-detail">
                        Running:{" "}
                        <strong>
                          {reason.running_kernel}
                        </strong>

                        {" → "}

                        Installed:{" "}
                        <strong>
                          {reason.installed_kernel}
                        </strong>
                      </div>
                    )}
                  </div>
                )
              )}
            </div>
          </div>
        )}

        {operationStatus && (
          <div
            className={
              operationStatus === "Operation failed."
                ? "operation-status failed"
                : busy
                  ? "operation-status working"
                  : "operation-status success"
            }
          >
            {busy ? (
              <span
                className="operation-spinner"
                aria-hidden="true"
              />
            ) : (
              <span
                className="operation-status-icon"
                aria-hidden="true"
              >
                {operationStatus === "Operation failed."
                  ? "!"
                  : "✓"}
              </span>
            )}

            <strong>
              {operationStatus}
            </strong>
          </div>
        )}

      <div className="update-toolbar">
          <button
            className="button primary"
            disabled={busy}
            onClick={() =>
              void refresh()
            }
          >
            Check Updates
          </button>

          {heldUpdates.length > 0 && (
            <button
              className="button"
              disabled={busy}
              onClick={() =>
                setShowHeldUpdates(
                  (current) => !current
                )
              }
            >
              {showHeldUpdates
                ? "Hide held packages"
                : `Show held packages (${heldUpdates.length})`}
            </button>
          )}

          <button
            className="button"
            disabled={
              busy ||
              result?.cleanup_available === false
            }
            onClick={async () => {
              if (!window.confirm(
                `Run package cleanup on ${server.name}?`
              )) {
                return;
              }

              setOperationStatus(
                "Running package cleanup…"
              );
              setBusy(true);

              try {
                await cleanupServer(
                  server.id
                );

                await refresh(
                  "Refreshing package state…"
                );

                setOperationStatus(
                  "Package cleanup completed successfully."
                );

              } catch (err) {
                setOperationStatus(
                  "Operation failed."
                );

                onError(
                  err instanceof Error
                    ? err.message
                    : "Package cleanup failed"
                );

              } finally {
                setBusy(false);
              }
            }}
          >
            Cleanup
          </button>

          {result?.cleanup_available !== undefined && (
            <span
              className={
                result.cleanup_available
                  ? "cleanup-status available"
                  : "cleanup-status clean"
              }
            >
              {result.cleanup_available
                ? "Cleanup available"
                : "Nothing to clean"}
            </span>
          )}

          <div className="update-toolbar-spacer" />

          <button
            className="button primary"
            disabled={
              busy ||
              selected.length === 0
            }
            onClick={async () => {
              if (!window.confirm(
                `Install ${selected.length} selected update(s) on ${server.name}?`
              )) {
                return;
              }

              setOperationStatus(
                "Installing selected updates…"
              );
              setBusy(true);

              try {
                await installSelectedUpdates(
                  server.id,
                  selected
                );

                await refresh(
                  "Refreshing package state…"
                );

                setOperationStatus(
                  "Selected updates installed successfully."
                );

              } catch (err) {
                setOperationStatus(
                  "Operation failed."
                );

                onError(
                  err instanceof Error
                    ? err.message
                    : "Selected update installation failed"
                );

              } finally {
                setBusy(false);
              }
            }}
          >
            Install Selected ({selected.length})
          </button>

          <button
            className="button primary"
            disabled={
              busy ||
              !result ||
              result.updates_available === 0
            }
            onClick={async () => {
              if (!window.confirm(
                `Install all available updates on ${server.name}?`
              )) {
                return;
              }

              setOperationStatus(
                "Installing all available updates…"
              );
              setBusy(true);

              try {
                await installAllUpdates(
                  server.id
                );

                await refresh(
                  "Refreshing package state…"
                );

                setOperationStatus(
                  "All available updates installed successfully."
                );

              } catch (err) {
                setOperationStatus(
                  "Operation failed."
                );

                onError(
                  err instanceof Error
                    ? err.message
                    : "Update installation failed"
                );

              } finally {
                setBusy(false);
              }
            }}
          >
            Install All
          </button>
        </div>

        {showHeldUpdates && heldUpdates.length > 0 && (
          <div className="held-updates-section">
            <div className="held-warning">
              <strong>
                Caution: Held packages
              </strong>

              <p>
                These packages were held back by the system
                and are excluded from normal updates.
                Updating them may require dependency changes
                or could affect system stability.
              </p>

              <p>
                Only proceed if you understand why they were
                held and have verified that the upgrade is safe.
              </p>

              <small>
                Held packages are never included in
                "Install All" or scheduled update installations.
                They can only be installed here through an
                explicit manual selection.
              </small>
            </div>

              <div className="table-wrap update-table held-table">
                <table>
                  <thead>
                    <tr>
                      <th />
                      <th>Lock</th>
                      <th>Status</th>
                      <th>Package</th>
                      <th>Installed</th>
                      <th>Available</th>
                    </tr>
                  </thead>

                  <tbody>
                    {heldUpdates.map(
                      (update) => (
                        <tr key={update.name}>
                          <td>
                            <input
                              type="checkbox"
                              disabled={
                                busy ||
                                Boolean(update.locked)
                              }
                              checked={
                                !update.locked &&
                                selectedHeld.includes(
                                  update.name
                                )
                              }
                              onChange={() =>
                                setSelectedHeld(
                                  (current) =>
                                    current.includes(
                                      update.name
                                    )
                                      ? current.filter(
                                          (item) =>
                                            item !== update.name
                                        )
                                      : [
                                          ...current,
                                          update.name
                                        ]
                                )
                              }
                            />
                          </td>

                          <td>
                            <button
                              type="button"
                              className={
                                update.locked
                                  ? "package-lock locked"
                                  : "package-lock"
                              }
                              disabled={busy}
                              title={
                                update.locked
                                  ? "Unlock package"
                                  : "Lock package"
                              }
                              onClick={() =>
                                void togglePackageLock(
                                  update
                                )
                              }
                            >
                              {update.locked ? "🔒" : "🔓"}
                            </button>
                          </td>

                          <td>
                            <span className="badge warning">
                              HELD
                            </span>
                          </td>

                          <td>{update.name}</td>
                          <td>{update.installed_version}</td>
                          <td>{update.available_version}</td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>

              <div className="held-install-actions">
                <button
                  className="button warning"
                  disabled={
                    busy ||
                    selectedHeld.length === 0
                  }
                  onClick={async () => {
                    const packageList =
                      selectedHeld.join(", ");

                    if (!window.confirm(
                      `WARNING: The following package(s) were held back by APT:

${packageList}

Installing held packages may require dependency changes or affect system stability. Continue only if you have verified that these upgrades are safe.

Proceed with installation?`
                    )) {
                      return;
                    }

                    setOperationStatus(
                      "Installing selected held packages…"
                    );
                    setBusy(true);

                    try {
                      await installHeldUpdates(
                        server.id,
                        selectedHeld
                      );

                      setSelectedHeld([]);

                      await refresh(
                        "Refreshing package state…"
                      );

                      setOperationStatus(
                        "Held packages installed successfully."
                      );

                    } catch (err) {
                      setOperationStatus(
                        "Operation failed."
                      );

                      onError(
                        err instanceof Error
                          ? err.message
                          : "Held package installation failed"
                      );

                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Install Selected Held Packages
                  {" "}
                  ({selectedHeld.length})
                </button>
              </div>
          </div>
        )}

        {!snapshotLoaded ? (
          <div className="update-not-checked">
            <strong>
              Loading last update status…
            </strong>
          </div>
        ) : !result ? (
          <div className="update-not-checked">
            <strong>
              Updates have not been checked yet.
            </strong>

            <span>
              Click "Check Updates" to retrieve the current
              package status from this server.
            </span>
          </div>
        ) : result.updates.length ? (
            <div className="table-wrap update-table">
              <table>
                <thead>
                  <tr>
                    <th />
                    <th>Lock</th>
                    <th>Package</th>
                    <th>Installed</th>
                    <th>Available</th>
                  </tr>
                </thead>

                <tbody>
                  {result.updates.map(
                    (update) => (
                      <tr key={update.name}>
                        <td>
                          <input
                            type="checkbox"
                            disabled={
                              busy ||
                              Boolean(update.locked)
                            }
                            checked={
                              !update.locked &&
                              selected.includes(
                                update.name
                              )
                            }
                            onChange={() =>
                              setSelected(
                                (current) =>
                                  current.includes(
                                    update.name
                                  )
                                    ? current.filter(
                                        (item) =>
                                          item !== update.name
                                      )
                                    : [
                                        ...current,
                                        update.name
                                      ]
                              )
                            }
                          />
                        </td>

                        <td>
                          <button
                            type="button"
                            className={
                              update.locked
                                ? "package-lock locked"
                                : "package-lock"
                            }
                            disabled={busy}
                            title={
                              update.locked
                                ? "Unlock package"
                                : "Lock package"
                            }
                            onClick={() =>
                              void togglePackageLock(
                                update
                              )
                            }
                          >
                            {update.locked ? "🔒" : "🔓"}
                          </button>
                        </td>

                        <td>{update.name}</td>
                        <td>{update.installed_version}</td>
                        <td>{update.available_version}</td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
        ) : (
          <div className="empty">
            System is up to date.
          </div>
        )}
      </div>
    </div>
  );
}


function ServerPanel({
  servers,
  onUpdates,
  onEdit,
  onDelete,
  onAdd
}: {
  servers: Server[];
  onUpdates: (server: Server) => void;
  onEdit: (server: Server) => void;
  onDelete: (server: Server) => void;
  onAdd: () => void;
}) {
  const [serverSearch, setServerSearch] =
    useState("");

  const [
    packageManagerFilter,
    setPackageManagerFilter
  ] = useState("ALL");

  const [
    statusFilter,
    setStatusFilter
  ] = useState("ALL");

  const normalizedServerSearch =
    serverSearch.trim().toLowerCase();

  const packageManagers = Array.from(
    new Set(
      servers
        .map(
          (server) =>
            server.package_manager
        )
        .filter(
          (manager): manager is string =>
            Boolean(manager)
        )
    )
  ).sort();

  const filteredServers = servers.filter(
    (server) => {
      const searchableValues = [
        server.name,
        server.system_hostname,
        server.host,
        server.distribution,
        server.package_manager,
        server.kernel_version
      ];

      const matchesSearch =
        !normalizedServerSearch ||
        searchableValues.some(
          (value) =>
            value?.toLowerCase().includes(
              normalizedServerSearch
            )
        );

      const matchesPackageManager =
        packageManagerFilter === "ALL" ||
        server.package_manager ===
          packageManagerFilter;

      const matchesStatus =
        statusFilter === "ALL" ||
        server.connection_status ===
          statusFilter;

      return (
        matchesSearch &&
        matchesPackageManager &&
        matchesStatus
      );
    }
  );

  function connectionStatusLabel(
    status: string
  ): string {
    switch (status) {
      case "ONLINE":
        return "Online";

      case "UNREACHABLE":
        return "Offline";

      case "AUTH_FAILED":
        return "Authentication failed";

      case "ERROR":
        return "Error";

      default:
        return "Unknown";
    }
  }

  function connectionStatusClass(
    status: string
  ): string {
    if (status === "ONLINE") {
      return "badge ok";
    }

    if (status === "UNKNOWN") {
      return "badge neutral";
    }

    return "badge danger";
  }

  return (
    <section className="panel server-list-panel">
      <div className="panel-header">
        <h2 className="panel-title">
          Servers
        </h2>

        <button
          className="button primary"
          onClick={onAdd}
        >
          + Add Server
        </button>
      </div>

      {servers.length > 0 && (
        <div className="server-list-toolbar">
          <div className="server-list-search">
            <input
              type="search"
              placeholder="Search servers..."
              value={serverSearch}
              onChange={(event) =>
                setServerSearch(
                  event.target.value
                )
              }
            />
          </div>

          <select
            className="server-list-filter"
            value={packageManagerFilter}
            onChange={(event) =>
              setPackageManagerFilter(
                event.target.value
              )
            }
          >
            <option value="ALL">
              All Package Managers
            </option>

            {packageManagers.map(
              (manager) => (
                <option
                  key={manager}
                  value={manager}
                >
                  {manager.toUpperCase()}
                </option>
              )
            )}
          </select>

          <select
            className="server-list-filter"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(
                event.target.value
              )
            }
          >
            <option value="ALL">
              All Statuses
            </option>
            <option value="ONLINE">
              Online
            </option>
            <option value="UNREACHABLE">
              Offline
            </option>
            <option value="AUTH_FAILED">
              Authentication failed
            </option>
            <option value="ERROR">
              Error
            </option>
            <option value="UNKNOWN">
              Unknown
            </option>
          </select>

          {(serverSearch ||
            packageManagerFilter !== "ALL" ||
            statusFilter !== "ALL") && (
            <button
              type="button"
              className="button"
              onClick={() => {
                setServerSearch("");
                setPackageManagerFilter("ALL");
                setStatusFilter("ALL");
              }}
            >
              Clear
            </button>
          )}
        </div>
      )}

      {servers.length === 0 ? (
        <div className="empty">
          No servers configured.
        </div>
      ) : filteredServers.length === 0 ? (
        <div className="empty">
          No servers match your filters.
        </div>
      ) : (
        <>
          <div className="server-table-wrap">
            <table className="server-table">
              <thead>
                <tr>
                  <th>Hostname</th>
                  <th>Distribution</th>
                  <th>Package Manager</th>
                  <th>Status</th>
                  <th>Kernel</th>
                  <th>Updates</th>
                  <th>Reboot</th>
                  <th>Cleanup</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredServers.map(
                  (server) => (
                    <tr key={server.id}>
                      <td>
                        <div className="server-list-name">
                          {server.name}
                        </div>

                        <div className="server-list-host">
                          {server.host}
                        </div>
                      </td>

                      <td className="server-list-distribution">
                        {server.distribution ??
                          "Unknown"}
                      </td>

                      <td>
                        <span
                          className={
                            server.package_manager
                              ? `package-manager-badge ${server.package_manager}`
                              : "package-manager-badge unknown"
                          }
                        >
                          {server.package_manager
                            ?.toUpperCase() ??
                            "Unknown"}
                        </span>
                      </td>

                      <td>
                        <span
                          className={connectionStatusClass(
                            server.connection_status
                          )}
                        >
                          {connectionStatusLabel(
                            server.connection_status
                          )}
                        </span>
                      </td>

                      <td className="server-list-kernel">
                        {server.kernel_version ??
                          "Unknown"}
                      </td>

                      <td>
                        <div className="server-list-updates">
                          <strong
                            className={
                              server.updates_available > 0
                                ? "text-warning"
                                : ""
                            }
                          >
                            {server.updates_available}
                          </strong>

                          <span>
                            {server.updates_available === 1
                              ? "update"
                              : "updates"}
                          </span>
                        </div>
                      </td>

                      <td>
                        {server.reboot_required ? (
                          <span className="badge warning">
                            Required
                          </span>
                        ) : (
                          <span className="badge ok">
                            No
                          </span>
                        )}
                      </td>

                      <td>
                        {server.cleanup_available === true ? (
                          <span className="cleanup-status available">
                            Available
                          </span>
                        ) : server.cleanup_available === false ? (
                          <span className="cleanup-status clean">
                            Clean
                          </span>
                        ) : (
                          <span className="badge neutral">
                            Unknown
                          </span>
                        )}
                      </td>
                      <td>
                        <div className="server-list-actions">
                          {server.connection_status ===
                            "ONLINE" && (
                            <button
                              className="button primary"
                              onClick={() =>
                                onUpdates(server)
                              }
                            >
                              Updates
                            </button>
                          )}

                          <button
                            className="button"
                            onClick={() =>
                              onEdit(server)
                            }
                          >
                            Edit
                          </button>

                          <button
                            className="button danger"
                            onClick={() =>
                              onDelete(server)
                            }
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>

          <div className="server-list-footer">
            Showing {filteredServers.length} of{" "}
            {servers.length} servers
          </div>
        </>
      )}
    </section>
  );
}



const NOTIFICATION_EVENT_LABELS: Record<string, string> = {
  SERVER_OFFLINE: "Server offline",
  SERVER_ONLINE: "Server online again",
  SSH_ERROR: "SSH error",
  UPDATES_AVAILABLE: "Updates available",
  INSTALL_SUCCESS: "Update installation successful",
  INSTALL_FAILED: "Update installation failed",
  CLEANUP_AVAILABLE: "Cleanup available",
  CLEANUP_SUCCESS: "Cleanup successful",
  CLEANUP_FAILED: "Cleanup failed",
  REBOOT_REQUIRED: "Reboot required",
  TASK_SUCCESS: "Scheduled task successful",
  TASK_FAILED: "Scheduled task failed"
};


const NOTIFICATION_EVENT_DESCRIPTIONS: Record<string, string> = {
  SERVER_OFFLINE:
    "A managed server becomes unreachable.",

  SERVER_ONLINE:
    "A previously unavailable server becomes reachable again.",

  SSH_ERROR:
    "An SSH connection or authentication error occurs.",

  UPDATES_AVAILABLE:
    "Package updates are detected on a managed server.",

  INSTALL_SUCCESS:
    "An update installation completes successfully.",

  INSTALL_FAILED:
    "An update installation fails.",

  CLEANUP_AVAILABLE:
    "Removable package leftovers are detected.",

  CLEANUP_SUCCESS:
    "A package cleanup completes successfully.",

  CLEANUP_FAILED:
    "A package cleanup fails.",

  REBOOT_REQUIRED:
    "A managed server requires a reboot.",

  TASK_SUCCESS:
    "A scheduled task completes successfully.",

  TASK_FAILED:
    "A scheduled task completes with a failure."
};


function SettingsPanel({
  taskTimezone,
  onTaskTimezoneChange
}: {
  taskTimezone: string;
  onTaskTimezoneChange: (timezone: string) => void;
}) {
  const [settings, setSettings] =
    useState<NotificationSettings | null>(null);

  const [loadingSettings, setLoadingSettings] =
    useState(true);

  const [savingSettings, setSavingSettings] =
    useState(false);

  const [savingEventKey, setSavingEventKey] =
    useState<string | null>(null);

  const [testingDiscord, setTestingDiscord] =
    useState(false);

  const [testingEmail, setTestingEmail] =
    useState(false);

  const [smtpPassword, setSmtpPassword] =
    useState("");

  const [discordWebhook, setDiscordWebhook] =
    useState("");

  const [recipientInput, setRecipientInput] =
    useState("");

  const [settingsError, setSettingsError] =
    useState<string | null>(null);

  const [settingsSuccess, setSettingsSuccess] =
    useState<string | null>(null);


  useEffect(() => {
    let cancelled = false;

    async function loadNotificationSettings() {
      setLoadingSettings(true);
      setSettingsError(null);

      try {
        const result =
          await getNotificationSettings();

        if (!cancelled) {
          setSettings(result);

          setRecipientInput(
            result.email_recipients.join("\n")
          );
        }

      } catch (err) {
        if (!cancelled) {
          setSettingsError(
            err instanceof Error
              ? err.message
              : "Unable to load notification settings"
          );
        }

      } finally {
        if (!cancelled) {
          setLoadingSettings(false);
        }
      }
    }

    void loadNotificationSettings();

    return () => {
      cancelled = true;
    };
  }, []);


  function updateLocalSettings(
    changes: Partial<NotificationSettings>
  ) {
    setSettings(
      (current) =>
        current
          ? {
              ...current,
              ...changes
            }
          : current
    );

    setSettingsSuccess(null);
  }


  async function updateEventPreference(
    eventKey: string,
    channel: "email" | "discord",
    enabled: boolean
  ) {
    if (!settings) {
      return;
    }

    const previousEvents =
      settings.events;

    const nextEvents: NotificationEventPreference[] =
      settings.events.map(
        (event) =>
          event.event_key === eventKey
            ? {
                ...event,
                [`${channel}_enabled`]:
                  enabled
              }
            : event
      );

    setSettings({
      ...settings,
      events: nextEvents
    });

    setSavingEventKey(eventKey);
    setSettingsError(null);
    setSettingsSuccess(null);

    try {
      const result =
        await saveNotificationEventPreferences(
          nextEvents
        );

      setSettings(result);

    } catch (err) {
      setSettings(
        (current) =>
          current
            ? {
                ...current,
                events: previousEvents
              }
            : current
      );

      setSettingsError(
        err instanceof Error
          ? err.message
          : "Unable to update notification event"
      );

    } finally {
      setSavingEventKey(null);
    }
  }


  async function toggleDiscordEnabled(
    enabled: boolean
  ) {
    if (!settings) {
      return;
    }

    const previous = settings.discord_enabled;

    updateLocalSettings({
      discord_enabled: enabled
    });

    setSettingsError(null);
    setSettingsSuccess(null);

    try {
      const result =
        await setDiscordNotificationEnabled(
          enabled
        );

      setSettings(result);

      setSettingsSuccess(
        enabled
          ? "Discord notifications enabled."
          : "Discord notifications disabled."
      );

    } catch (err) {
      updateLocalSettings({
        discord_enabled: previous
      });

      setSettingsError(
        err instanceof Error
          ? err.message
          : "Unable to update Discord notification status"
      );
    }
  }


  async function toggleEmailEnabled(
    enabled: boolean
  ) {
    if (!settings) {
      return;
    }

    const previous = settings.email_enabled;

    updateLocalSettings({
      email_enabled: enabled
    });

    setSettingsError(null);
    setSettingsSuccess(null);

    try {
      const result =
        await setEmailNotificationEnabled(
          enabled
        );

      setSettings(result);

      setSettingsSuccess(
        enabled
          ? "Email notifications enabled."
          : "Email notifications disabled."
      );

    } catch (err) {
      updateLocalSettings({
        email_enabled: previous
      });

      setSettingsError(
        err instanceof Error
          ? err.message
          : "Unable to update Email notification status"
      );
    }
  }


  async function saveDiscordSettings() {
    if (!settings) {
      return;
    }

    setSavingSettings(true);
    setSettingsError(null);
    setSettingsSuccess(null);

    try {
      const result =
        await saveDiscordNotificationSettings({
          discord_enabled:
            settings.discord_enabled,

          discord_webhook_url:
            discordWebhook || null
        });

      setSettings(result);
      setDiscordWebhook("");

      setSettingsSuccess(
        "Discord settings saved."
      );

    } catch (err) {
      setSettingsError(
        err instanceof Error
          ? err.message
          : "Unable to save Discord settings"
      );

    } finally {
      setSavingSettings(false);
    }
  }


  async function saveEmailSettings() {
    if (!settings) {
      return;
    }

    setSavingSettings(true);
    setSettingsError(null);
    setSettingsSuccess(null);

    const recipients = recipientInput
      .split(/\r?\n|,/)
      .map((value) => value.trim())
      .filter(Boolean);

    try {
      const result =
        await saveEmailNotificationSettings({
          email_enabled:
            settings.email_enabled,

          smtp_host:
            settings.smtp_host,

          smtp_port:
            settings.smtp_port,

          smtp_security:
            settings.smtp_security,

          smtp_username:
            settings.smtp_username,

          smtp_password:
            smtpPassword || null,

          email_from:
            settings.email_from,

          email_recipients:
            recipients
        });

      setSettings(result);

      setRecipientInput(
        result.email_recipients.join("\n")
      );

      setSmtpPassword("");

      setSettingsSuccess(
        "Email settings saved."
      );

    } catch (err) {
      setSettingsError(
        err instanceof Error
          ? err.message
          : "Unable to save Email settings"
      );

    } finally {
      setSavingSettings(false);
    }
  }


  async function sendDiscordTest() {
    if (!settings) {
      return;
    }

    setTestingDiscord(true);
    setSettingsError(null);
    setSettingsSuccess(null);

    try {
      await testNotification({
        channel: "discord",
        discord_webhook_url:
          discordWebhook || null
      });

      setSettingsSuccess(
        "Discord test notification sent successfully."
      );

    } catch (err) {
      setSettingsError(
        err instanceof Error
          ? err.message
          : "Unable to send Discord test notification"
      );

    } finally {
      setTestingDiscord(false);
    }
  }


  async function sendEmailTest() {
    if (!settings) {
      return;
    }

    setTestingEmail(true);
    setSettingsError(null);
    setSettingsSuccess(null);

    try {
      const recipients = recipientInput
        .split(/\r?\n|,/)
        .map((value) => value.trim())
        .filter(Boolean);

      await testNotification({
        channel: "email",

        smtp_host:
          settings.smtp_host,

        smtp_port:
          settings.smtp_port,

        smtp_security:
          settings.smtp_security,

        smtp_username:
          settings.smtp_username,

        smtp_password:
          smtpPassword || null,

        email_from:
          settings.email_from,

        email_recipients:
          recipients
      });

      setSettingsSuccess(
        "Email test notification sent successfully."
      );

    } catch (err) {
      setSettingsError(
        err instanceof Error
          ? err.message
          : "Unable to send email test notification"
      );

    } finally {
      setTestingEmail(false);
    }
  }


  async function deleteDiscordConfiguration() {
    if (!window.confirm(
      "Delete the complete Discord notification configuration?"
    )) {
      return;
    }

    setSettingsError(null);
    setSettingsSuccess(null);

    try {
      const result =
        await deleteDiscordNotificationSettings();

      setSettings(result);
      setDiscordWebhook("");

      setSettingsSuccess(
        "Discord notification configuration deleted."
      );

    } catch (err) {
      setSettingsError(
        err instanceof Error
          ? err.message
          : "Unable to delete Discord configuration"
      );
    }
  }


  async function deleteEmailConfiguration() {
    if (!window.confirm(
      "Delete the complete email notification configuration?"
    )) {
      return;
    }

    setSettingsError(null);
    setSettingsSuccess(null);

    try {
      const result =
        await deleteEmailNotificationSettings();

      setSettings(result);
      setSmtpPassword("");

      setRecipientInput(
        result.email_recipients.join("\n")
      );

      setSettingsSuccess(
        "Email notification configuration deleted."
      );

    } catch (err) {
      setSettingsError(
        err instanceof Error
          ? err.message
          : "Unable to delete email configuration"
      );
    }
  }


  if (loadingSettings) {
    return (
      <section className="panel">
        <div className="loading">
          Loading notification settings…
        </div>
      </section>
    );
  }


  if (!settings) {
    return (
      <section className="panel">
        <div className="error-box">
          Notification settings could not be loaded.
        </div>
      </section>
    );
  }


  return (
    <div className="settings-page">
      {settingsError && (
        <div className="error-box">
          {settingsError}
        </div>
      )}

      {settingsSuccess && (
        <div className="operation-status success">
          <span className="operation-status-icon">
            ✓
          </span>

          <span>
            {settingsSuccess}
          </span>
        </div>
      )}

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">
              General
            </h2>

            <p className="settings-description">
              Global application defaults.
            </p>
          </div>
        </div>

        <div className="settings-form-grid">
          <label>
            <span>Default Task Timezone</span>

            <select
              value={taskTimezone}
              onChange={(event) =>
                onTaskTimezoneChange(
                  event.target.value
                )
              }
            >
              {getTimezones().map(
                (zone) => (
                  <option
                    key={zone}
                    value={zone}
                  >
                    {zone}
                  </option>
                )
              )}
            </select>

            <small className="form-help">
              Used as the default timezone when creating
              new scheduled tasks.
            </small>
          </label>
        </div>
      </section>


      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">
              Discord
            </h2>

            <p className="settings-description">
              Send PatchForge notifications to a
              Discord channel using an incoming webhook.
            </p>
          </div>

          <label className="settings-switch">
            <span>
              Enabled
            </span>

            <input
              type="checkbox"
              role="switch"
              checked={settings.discord_enabled}
              onChange={(event) =>
                void toggleDiscordEnabled(
                  event.target.checked
                )
              }
            />

            <span
              className="settings-switch-track"
              aria-hidden="true"
            >
              <span className="settings-switch-thumb" />
            </span>
          </label>
        </div>

        <div className="settings-form-grid">
          <label className="form-full">
            <span>Webhook URL</span>

            <input
              type="password"
              value={discordWebhook}
              placeholder={
                settings.discord_webhook_configured
                  ? "Webhook configured — enter a new value to replace it"
                  : "https://discord.com/api/webhooks/..."
              }
              onChange={(event) =>
                setDiscordWebhook(
                  event.target.value
                )
              }
              autoComplete="new-password"
            />
          </label>

          <div className="form-full settings-secret-state">
            {settings.discord_webhook_configured ? (
              <span className="badge ok">
                Webhook configured
              </span>
            ) : (
              <span className="badge neutral">
                No webhook configured
              </span>
            )}
          </div>

          <div className="form-full settings-channel-actions">
            <button
              type="button"
              className="button primary"
              disabled={savingSettings}
              onClick={() =>
                void saveDiscordSettings()
              }
            >
              {savingSettings
                ? "Saving…"
                : "Save Discord"}
            </button>

            <button
              type="button"
              className="button"
              disabled={
                testingDiscord ||
                savingSettings ||
                !settings.discord_webhook_configured
              }
              onClick={() =>
                void sendDiscordTest()
              }
            >
              {testingDiscord
                ? "Sending…"
                : "Send Test Message"}
            </button>

            <button
              type="button"
              className="button danger"
              disabled={
                savingSettings ||
                !settings.discord_webhook_configured
              }
              onClick={() =>
                void deleteDiscordConfiguration()
              }
            >
              Delete Discord Configuration
            </button>
          </div>
        </div>
      </section>


      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">
              Email
            </h2>

            <p className="settings-description">
              Send notifications through an SMTP server.
            </p>
          </div>

          <label className="settings-switch">
            <span>
              Enabled
            </span>

            <input
              type="checkbox"
              role="switch"
              checked={settings.email_enabled}
              onChange={(event) =>
                void toggleEmailEnabled(
                  event.target.checked
                )
              }
            />

            <span
              className="settings-switch-track"
              aria-hidden="true"
            >
              <span className="settings-switch-thumb" />
            </span>
          </label>
        </div>

        <div className="settings-form-grid">
          <label>
            <span>SMTP Host</span>

            <input
              value={settings.smtp_host ?? ""}
              onChange={(event) =>
                updateLocalSettings({
                  smtp_host:
                    event.target.value
                })
              }
              placeholder="smtp.example.com"
            />
          </label>

          <label>
            <span>SMTP Port</span>

            <input
              type="number"
              min={1}
              max={65535}
              value={settings.smtp_port}
              onChange={(event) =>
                updateLocalSettings({
                  smtp_port:
                    Number(event.target.value)
                    || 587
                })
              }
            />
          </label>

          <label>
            <span>Security</span>

            <select
              value={settings.smtp_security}
              onChange={(event) =>
                updateLocalSettings({
                  smtp_security:
                    event.target.value as
                      NotificationSettings[
                        "smtp_security"
                      ]
                })
              }
            >
              <option value="starttls">
                STARTTLS
              </option>

              <option value="tls">
                TLS / SSL
              </option>

              <option value="none">
                None
              </option>
            </select>
          </label>

          <label>
            <span>Username</span>

            <input
              value={settings.smtp_username ?? ""}
              onChange={(event) =>
                updateLocalSettings({
                  smtp_username:
                    event.target.value
                })
              }
              autoComplete="username"
            />
          </label>

          <label>
            <span>Password</span>

            <input
              type="password"
              value={smtpPassword}
              placeholder={
                settings.smtp_password_configured
                  ? "Password configured — enter a new value to replace it"
                  : "SMTP password"
              }
              onChange={(event) =>
                setSmtpPassword(
                  event.target.value
                )
              }
              autoComplete="new-password"
            />
          </label>

          <label>
            <span>From Address</span>

            <input
              type="email"
              value={settings.email_from ?? ""}
              onChange={(event) =>
                updateLocalSettings({
                  email_from:
                    event.target.value
                })
              }
              placeholder="patchforge@example.com"
            />
          </label>

          <label className="form-full">
            <span>Recipients</span>

            <textarea
              value={recipientInput}
              onChange={(event) =>
                setRecipientInput(
                  event.target.value
                )
              }
              rows={4}
              placeholder={
                "admin@example.com\nops@example.com"
              }
            />

            <small className="form-help">
              Enter one address per line or separate
              multiple addresses with commas.
            </small>
          </label>

          <div className="form-full settings-secret-state">
            {settings.smtp_password_configured ? (
              <span className="badge ok">
                SMTP password configured
              </span>
            ) : (
              <span className="badge neutral">
                No SMTP password configured
              </span>
            )}
          </div>

          <div className="form-full settings-channel-actions">
            <button
              type="button"
              className="button primary"
              disabled={savingSettings}
              onClick={() =>
                void saveEmailSettings()
              }
            >
              {savingSettings
                ? "Saving…"
                : "Save Email"}
            </button>

            <button
              type="button"
              className="button"
              disabled={
                testingEmail ||
                savingSettings ||
                !settings.smtp_host
              }
              onClick={() =>
                void sendEmailTest()
              }
            >
              {testingEmail
                ? "Sending…"
                : "Send Test Email"}
            </button>

            <button
              type="button"
              className="button danger"
              disabled={
                savingSettings ||
                (
                  !settings.smtp_host &&
                  !settings.smtp_password_configured &&
                  !settings.email_from &&
                  settings.email_recipients.length === 0
                )
              }
              onClick={() =>
                void deleteEmailConfiguration()
              }
            >
              Delete Email Configuration
            </button>
          </div>
        </div>
      </section>


      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">
              Notification Events
            </h2>

            <p className="settings-description">
              Choose which events are sent through each
              notification channel.
            </p>
          </div>
        </div>

        <div className="notification-event-grid">
          {settings.events.map(
            (event) => (
              <div
                key={event.event_key}
                className={
                  `notification-event-card ${
                    savingEventKey === event.event_key
                      ? "saving"
                      : ""
                  }`
                }
              >
                <div className="notification-event-content">
                  <div className="notification-event-name">
                    {NOTIFICATION_EVENT_LABELS[
                      event.event_key
                    ] ?? event.event_key}
                  </div>

                  <div className="notification-event-description">
                    {NOTIFICATION_EVENT_DESCRIPTIONS[
                      event.event_key
                    ] ?? event.event_key}
                  </div>
                </div>

                <div className="notification-event-switches">
                  <label className="event-switch">
                    <span>
                      Email
                    </span>

                    <input
                      type="checkbox"
                      role="switch"
                      checked={event.email_enabled}
                      disabled={savingEventKey !== null}
                      onChange={(changeEvent) =>
                        void updateEventPreference(
                          event.event_key,
                          "email",
                          changeEvent.target.checked
                        )
                      }
                    />

                    <span
                      className="settings-switch-track"
                      aria-hidden="true"
                    >
                      <span className="settings-switch-thumb" />
                    </span>
                  </label>

                  <label className="event-switch">
                    <span>
                      Discord
                    </span>

                    <input
                      type="checkbox"
                      role="switch"
                      checked={event.discord_enabled}
                      disabled={savingEventKey !== null}
                      onChange={(changeEvent) =>
                        void updateEventPreference(
                          event.event_key,
                          "discord",
                          changeEvent.target.checked
                        )
                      }
                    />

                    <span
                      className="settings-switch-track"
                      aria-hidden="true"
                    >
                      <span className="settings-switch-thumb" />
                    </span>
                  </label>
                </div>
              </div>
            )
          )}
        </div>
      </section>
    </div>
  );
}


function HistoryPanel({
  history,
  taskRuns = [],
  allowClear = false,
  retentionDays,
  onRetentionChange,
  onClear
}: {
  history: HistoryEntry[];
  taskRuns?: TaskRunSummary[];
  allowClear?: boolean;
  retentionDays?: number | null;
  onRetentionChange?: (
    days: number | null
  ) => void;
  onClear?: () => void;
}) {
  const [selectedRun, setSelectedRun] =
    useState<TaskRunDetail | null>(null);

  const [loadingRun, setLoadingRun] =
    useState(false);

  const [runError, setRunError] =
    useState<string | null>(null);


  const combinedHistory = useMemo(
    () => {
      const manualEntries = history.map(
        (entry) => ({
          kind: "history" as const,
          timestamp: entry.created_at,
          entry
        })
      );

      const taskEntries = taskRuns.map(
        (run) => ({
          kind: "task-run" as const,
          timestamp: run.started_at,
          run
        })
      );

      return [
        ...manualEntries,
        ...taskEntries
      ].sort(
        (a, b) =>
          new Date(b.timestamp).getTime()
          - new Date(a.timestamp).getTime()
      );
    },
    [
      history,
      taskRuns
    ]
  );


  async function openHistoryRun(
    run: TaskRunSummary
  ) {
    setLoadingRun(true);
    setRunError(null);

    try {
      const detail = await getTaskRun(
        run.task_id,
        run.id
      );

      setSelectedRun(detail);

    } catch (err) {
      setRunError(
        err instanceof Error
          ? err.message
          : "Unable to load task run details"
      );

    } finally {
      setLoadingRun(false);
    }
  }


  return (
    <section className="panel">
      <div className="panel-header">
        <h2 className="panel-title">
          History
        </h2>

        {allowClear && (
          <div className="history-actions">
            <label className="history-retention">
              <span>
                Retention
              </span>

              <select
                value={
                  retentionDays === null
                    ? "unlimited"
                    : String(retentionDays ?? 7)
                }
                onChange={(event) => {
                  const value =
                    event.target.value;

                  onRetentionChange?.(
                    value === "unlimited"
                      ? null
                      : Number(value)
                  );
                }}
              >
                <option value="7">
                  7 days
                </option>

                <option value="14">
                  14 days
                </option>

                <option value="30">
                  30 days
                </option>

                <option value="60">
                  60 days
                </option>

                <option value="90">
                  90 days
                </option>

                <option value="180">
                  180 days
                </option>

                <option value="365">
                  365 days
                </option>

                <option value="unlimited">
                  Unlimited
                </option>
              </select>
            </label>

            {history.length > 0 && (
              <button
                className="button danger"
                onClick={onClear}
              >
                Clear History
              </button>
            )}
          </div>
        )}
      </div>

      {combinedHistory.length === 0 ? (
        <div className="empty">
          No history entries.
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Source</th>
                <th>Action</th>
                <th>Status</th>
                <th>Result</th>
                <th>Reboot</th>
                <th>Message</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              {combinedHistory.map(
                (item) => {
                  if (item.kind === "task-run") {
                    const run = item.run;

                    return (
                      <tr
                        key={`task-run-${run.id}`}
                        className="history-task-run-row"
                        onClick={() =>
                          void openHistoryRun(run)
                        }
                      >
                        <td>
                          {formatDate(
                            run.started_at
                          )}
                        </td>

                        <td>
                          <strong>
                            {run.task_name}
                          </strong>

                          <div className="server-host">
                            {run.target_count} target(s)
                          </div>
                        </td>

                        <td>
                          {run.action}
                        </td>

                        <td>
                          <span
                            className={
                              run.status === "SUCCESS"
                                ? "badge ok"
                                : (
                                    run.status === "PARTIAL"
                                      ? "badge warning"
                                      : "badge danger"
                                  )
                            }
                          >
                            {run.status}
                          </span>
                        </td>

                        <td>
                          <div>
                            {run.success_count} successful
                          </div>

                          <div>
                            {run.failed_count} failed
                          </div>

                          {run.action === "CHECK" && (
                            <div>
                              {run.updates_found} update(s)
                            </div>
                          )}
                        </td>

                        <td>
                          —
                        </td>

                        <td>
                          Scheduled task run
                        </td>

                        <td>
                          <span className="history-open-hint">
                            Open
                          </span>
                        </td>
                      </tr>
                    );
                  }

                  const entry = item.entry;

                  return (
                    <tr key={`history-${entry.id}`}>
                      <td>
                        {formatDate(
                          entry.created_at
                        )}
                      </td>

                      <td>
                        {entry.server_name}
                      </td>

                      <td>
                        {entry.action}
                      </td>

                      <td>
                        <span
                          className={
                            entry.status === "SUCCESS"
                              ? "badge ok"
                              : "badge warning"
                          }
                        >
                          {entry.status}
                        </span>
                      </td>

                      <td>
                        {entry.package_count}
                      </td>

                      <td>
                        {entry.reboot_required
                          ? "Required"
                          : "No"}
                      </td>

                      <td>
                        {entry.message ?? ""}
                      </td>

                      <td></td>
                    </tr>
                  );
                }
              )}
            </tbody>
          </table>
        </div>
      )}

      {(loadingRun || selectedRun || runError) && (
        <div className="modal-backdrop">
          <div className="modal modal-update">
            <div className="update-header">
              <div>
                <h2>
                  History Run Details
                </h2>

                {selectedRun && (
                  <div className="server-host">
                    {selectedRun.task_name}
                    {" · "}
                    {selectedRun.action}
                  </div>
                )}
              </div>

              <button
                type="button"
                className="button"
                onClick={() => {
                  setSelectedRun(null);
                  setRunError(null);
                }}
              >
                Close
              </button>
            </div>

            {loadingRun ? (
              <div className="loading">
                Loading task run details…
              </div>

            ) : runError ? (
              <div className="error-box">
                {runError}
              </div>

            ) : selectedRun ? (
              <>
                <div className="update-summary">
                  <div>
                    <span>Status</span>
                    <strong>
                      {selectedRun.status}
                    </strong>
                  </div>

                  <div>
                    <span>Successful</span>
                    <strong>
                      {selectedRun.success_count}
                    </strong>
                  </div>

                  <div>
                    <span>Failed</span>
                    <strong>
                      {selectedRun.failed_count}
                    </strong>
                  </div>
                </div>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Server</th>
                        <th>Status</th>
                        <th>Result</th>
                        <th>Reboot</th>
                      </tr>
                    </thead>

                    <tbody>
                      {selectedRun.results.map(
                        (result) => (
                          <tr key={result.id}>
                            <td>
                              <strong>
                                {result.server_name}
                              </strong>

                              <div className="server-host">
                                {result.host}
                              </div>
                            </td>

                            <td>
                              <span
                                className={
                                  result.status === "SUCCESS"
                                    ? "badge ok"
                                    : "badge danger"
                                }
                              >
                                {result.status}
                              </span>
                            </td>

                            <td>
                              {selectedRun.action === "CHECK" && (
                                <>
                                  <strong>
                                    {result.update_count} update(s)
                                  </strong>

                                  {result.updates.length > 0 && (
                                    <div className="task-run-packages">
                                      {result.updates.map(
                                        (pkg) => (
                                          <div key={pkg}>
                                            {pkg}
                                          </div>
                                        )
                                      )}
                                    </div>
                                  )}
                                </>
                              )}

                              {selectedRun.action === "INSTALL_ALL" && (
                                <>
                                  <strong>
                                    {result.installed_count} installed
                                  </strong>

                                  {result.installed_packages.length > 0 && (
                                    <div className="task-run-packages">
                                      {result.installed_packages.map(
                                        (pkg) => (
                                          <div key={pkg}>
                                            {pkg}
                                          </div>
                                        )
                                      )}
                                    </div>
                                  )}

                                  <div className="server-host">
                                    Remaining updates:{" "}
                                    {result.remaining_updates}
                                  </div>
                                </>
                              )}

                              {selectedRun.action === "CLEANUP" && (
                                <span>
                                  Cleanup completed
                                </span>
                              )}

                              {selectedRun.action === "REBOOT_CHECK" && (
                                <span>
                                  Reboot status checked
                                </span>
                              )}

                              {result.error && (
                                <div className="task-run-error">
                                  {result.error}
                                </div>
                              )}
                            </td>

                            <td>
                              <span
                                className={
                                  result.reboot_required
                                    ? "badge warning"
                                    : "badge ok"
                                }
                              >
                                {result.reboot_required
                                  ? "Required"
                                  : "No"}
                              </span>
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

    </section>
  );
}

export default App;
