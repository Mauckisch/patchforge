import type {
  CleanupResult,
  HistoryEntry,
  InstallResult,
  NotificationSettings,
  NotificationSettingsUpdate,
  NotificationTestResult,
  RebootStatus,
  ScheduledTask,
  Server,
  TaskRunDetail,
  TaskRunSummary,
  UpdateResult
} from "./types";


async function request<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(
    url,
    options
  );

  if (!response.ok) {
    let message = `HTTP ${response.status}`;

    try {
      const data = await response.json();

      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (
        data.detail &&
        typeof data.detail.message === "string"
      ) {
        message = data.detail.message;
      }
    } catch {
      // Keep generic HTTP error.
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}


export function getServers(): Promise<Server[]> {
  return request<Server[]>("/api/servers");
}


export function getTasks(): Promise<ScheduledTask[]> {
  return request<ScheduledTask[]>("/api/tasks");
}


export function getTaskRuns(
  taskId: number
): Promise<TaskRunSummary[]> {
  return request<TaskRunSummary[]>(
    `/api/tasks/${taskId}/runs`
  );
}


export function getTaskRun(
  taskId: number,
  runId: number
): Promise<TaskRunDetail> {
  return request<TaskRunDetail>(
    `/api/tasks/${taskId}/runs/${runId}`
  );
}


export function getTaskRunHistory(): Promise<TaskRunSummary[]> {
  return request<TaskRunSummary[]>(
    "/api/history/task-runs"
  );
}


export function getHistory(): Promise<HistoryEntry[]> {
  return request<HistoryEntry[]>("/api/history");
}


export function checkUpdates(
  serverId: number
): Promise<UpdateResult> {
  return request<UpdateResult>(
    `/api/servers/${serverId}/updates/check`,
    {
      method: "POST"
    }
  );
}


export function installSelectedUpdates(
  serverId: number,
  packages: string[]
): Promise<{
  status: string;
  server_id: number;
  operation: string;
  message: string;
}> {
  return request<{
    status: string;
    server_id: number;
    operation: string;
    message: string;
  }>(
    `/api/servers/${serverId}/updates/install`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        packages
      })
    }
  );
}


export function installAllUpdates(
  serverId: number
): Promise<{
  status: string;
  server_id: number;
  operation: string;
  message: string;
}> {
  return request<{
    status: string;
    server_id: number;
    operation: string;
    message: string;
  }>(
    `/api/servers/${serverId}/updates/install-all`,
    {
      method: "POST"
    }
  );
}


export function cleanupServer(
  serverId: number
): Promise<CleanupResult> {
  return request<CleanupResult>(
    `/api/servers/${serverId}/cleanup`,
    {
      method: "POST"
    }
  );
}


export function getRebootStatus(
  serverId: number
): Promise<RebootStatus> {
  return request<RebootStatus>(
    `/api/servers/${serverId}/reboot-status`
  );
}


export function deleteServer(
  serverId: number
): Promise<void> {
  return request<void>(
    `/api/servers/${serverId}`,
    {
      method: "DELETE"
    }
  );
}


export interface CreateServerPayload {
  name?: string | null;
  use_system_hostname: boolean;
  use_fqdn: boolean;
  host: string;
  ssh_port: number;
  username: string;
}


export interface CredentialPayload {
  ssh_password: string;
  privilege_method: "auto" | "sudo" | "su" | "none";
  privilege_password?: string;
}


export function createServer(
  payload: CreateServerPayload
): Promise<Server> {
  return request<Server>(
    "/api/servers",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }
  );
}


export function setServerCredentials(
  serverId: number,
  payload: CredentialPayload
): Promise<void> {
  return request<void>(
    `/api/servers/${serverId}/credentials`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }
  );
}


export function discoverServer(
  serverId: number
): Promise<Server> {
  return request<Server>(
    `/api/servers/${serverId}/discover`,
    {
      method: "POST"
    }
  );
}


export function privilegeCheck(
  serverId: number
): Promise<{
  available: boolean;
  method: string;
  password_required: boolean;
}> {
  return request(
    `/api/servers/${serverId}/privilege-check`,
    {
      method: "POST"
    }
  );
}


export interface CreateTaskPayload {
  name: string;
  server_ids: number[];
  action: "CHECK" | "INSTALL_ALL" | "CLEANUP" | "REBOOT_CHECK";
  schedule_type: "once" | "daily" | "weekly" | "monthly";
  timezone: string;
  run_at?: string;
  hour?: number;
  minute?: number;
  weekday?: number;
  day_of_month?: number;
  enabled: boolean;
  notify_only_on_updates: boolean;
}


export function createTask(
  payload: CreateTaskPayload
): Promise<ScheduledTask> {
  return request<ScheduledTask>(
    "/api/tasks",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }
  );
}


export function updateTask(
  taskId: number,
  payload: CreateTaskPayload
): Promise<ScheduledTask> {
  return request<ScheduledTask>(
    `/api/tasks/${taskId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }
  );
}


export function deleteTask(
  taskId: number
): Promise<void> {
  return request<void>(
    `/api/tasks/${taskId}`,
    {
      method: "DELETE"
    }
  );
}


export function runTaskNow(
  taskId: number
): Promise<{
  task_id: number;
  name: string;
  action: string;
  last_run_at: string | null;
  next_run_at: string | null;
  enabled: boolean;
}> {
  return request(
    `/api/tasks/${taskId}/run`,
    {
      method: "POST"
    }
  );
}


export interface UpdateServerPayload {
  name?: string | null;
  use_system_hostname?: boolean;
  use_fqdn?: boolean;
  host?: string;
  ssh_port?: number;
  username?: string;
}


export function updateServer(
  serverId: number,
  payload: UpdateServerPayload
): Promise<Server> {
  return request<Server>(
    `/api/servers/${serverId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }
  );
}


export function getCredentialStatus(
  serverId: number
): Promise<{
  configured: boolean;
  privilege_method: "auto" | "sudo" | "su" | "none";
  separate_privilege_password: boolean;
}> {
  return request(
    `/api/servers/${serverId}/credentials`
  );
}


export function clearHistory(): Promise<void> {
  return request<void>(
    "/api/history",
    {
      method: "DELETE"
    }
  );
}


export function clearServerHistory(
  serverId: number
): Promise<void> {
  return request<void>(
    `/api/servers/${serverId}/history`,
    {
      method: "DELETE"
    }
  );
}


export interface AppSettings {
  history_retention_days: number | null;
}


export function getSettings(): Promise<AppSettings> {
  return request<AppSettings>(
    "/api/settings"
  );
}


export function updateSettings(
  historyRetentionDays: number | null
): Promise<AppSettings> {
  return request<AppSettings>(
    "/api/settings",
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        history_retention_days:
          historyRetentionDays
      })
    }
  );
}


export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}


export function getHealth(
): Promise<HealthResponse> {
  return request<HealthResponse>(
    "/api/health"
  );
}


export function getNotificationSettings(
): Promise<NotificationSettings> {
  return request<NotificationSettings>(
    "/api/notifications/settings"
  );
}


export function updateNotificationSettings(
  payload: NotificationSettingsUpdate
): Promise<NotificationSettings> {
  return request<NotificationSettings>(
    "/api/notifications/settings",
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }
  );
}


export function testNotification(
  payload: {
    channel: "email" | "discord";

    discord_webhook_url?: string | null;

    smtp_host?: string | null;
    smtp_port?: number | null;
    smtp_security?: "none" | "starttls" | "tls" | null;
    smtp_username?: string | null;
    smtp_password?: string | null;
    email_from?: string | null;
    email_recipients?: string[] | null;
  }
): Promise<NotificationTestResult> {
  return request<NotificationTestResult>(
    "/api/notifications/test",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }
  );
}


export function deleteDiscordNotificationSettings(
): Promise<NotificationSettings> {
  return request<NotificationSettings>(
    "/api/notifications/settings/discord",
    {
      method: "DELETE"
    }
  );
}


export function deleteEmailNotificationSettings(
): Promise<NotificationSettings> {
  return request<NotificationSettings>(
    "/api/notifications/settings/email",
    {
      method: "DELETE"
    }
  );
}


export function saveDiscordNotificationSettings(
  payload: {
    discord_enabled: boolean;
    discord_webhook_url?: string | null;
  }
): Promise<NotificationSettings> {
  return request<NotificationSettings>(
    "/api/notifications/settings/discord",
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }
  );
}


export function saveEmailNotificationSettings(
  payload: {
    email_enabled: boolean;
    smtp_host: string | null;
    smtp_port: number;
    smtp_security: "none" | "starttls" | "tls";
    smtp_username: string | null;
    smtp_password?: string | null;
    email_from: string | null;
    email_recipients: string[];
  }
): Promise<NotificationSettings> {
  return request<NotificationSettings>(
    "/api/notifications/settings/email",
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }
  );
}


export function setDiscordNotificationEnabled(
  enabled: boolean
): Promise<NotificationSettings> {
  return request<NotificationSettings>(
    "/api/notifications/settings/discord/enabled",
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        enabled
      })
    }
  );
}


export function setEmailNotificationEnabled(
  enabled: boolean
): Promise<NotificationSettings> {
  return request<NotificationSettings>(
    "/api/notifications/settings/email/enabled",
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        enabled
      })
    }
  );
}


export function saveNotificationEventPreferences(
  events: NotificationSettings["events"]
): Promise<NotificationSettings> {
  return request<NotificationSettings>(
    "/api/notifications/settings/events",
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        events
      })
    }
  );
}


export function checkAllServerStatus(): Promise<{
  checked: number;
}> {
  return request(
    "/api/servers/status-check",
    {
      method: "POST"
    }
  );
}


export function checkServerStatus(
  serverId: number
): Promise<{
  server_id: number;
  status: string;
  last_seen_at: string | null;
  last_check_at: string | null;
  last_error: string | null;
}> {
  return request(
    `/api/servers/${serverId}/status-check`,
    {
      method: "POST"
    }
  );
}


export interface UpdateSnapshot {
  server_id: number;
  server: string;
  system_hostname: string | null;
  package_manager: string | null;
  updates_available: number;
  held_updates_available: number;
  updates_checked_at: string | null;
  reboot_required: boolean;

  updates: {
    name: string;
    installed_version: string;
    available_version: string;
    locked: boolean;
  }[];

  held_updates: {
    name: string;
    installed_version: string;
    available_version: string;
    held: true;
    locked: boolean;
  }[];
}


export function getUpdateSnapshot(
  serverId: number
): Promise<UpdateSnapshot> {
  return request<UpdateSnapshot>(
    `/api/servers/${serverId}/updates/snapshot`
  );
}


export function installHeldUpdates(
  serverId: number,
  packages: string[]
): Promise<InstallResult> {
  return request<InstallResult>(
    `/api/servers/${serverId}/updates/install-held`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        packages
      })
    }
  );
}


export function lockUpdatePackage(
  serverId: number,
  packageName: string
): Promise<{
  server_id: number;
  package_name: string;
  locked: boolean;
}> {
  return request(
    `/api/servers/${serverId}/updates/locks/${encodeURIComponent(packageName)}`,
    {
      method: "POST"
    }
  );
}


export function unlockUpdatePackage(
  serverId: number,
  packageName: string
): Promise<{
  server_id: number;
  package_name: string;
  locked: boolean;
}> {
  return request(
    `/api/servers/${serverId}/updates/locks/${encodeURIComponent(packageName)}`,
    {
      method: "DELETE"
    }
  );
}


export interface HostnamePreviewResponse {
  hostname: string;
  fqdn: string;
  domain: string;
}


export function previewServerHostname(
  serverId: number
): Promise<HostnamePreviewResponse> {
  return request<HostnamePreviewResponse>(
    `/api/servers/${serverId}/hostname-preview`,
    {
      method: "POST"
    }
  );
}
