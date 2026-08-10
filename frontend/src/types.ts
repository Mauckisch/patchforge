export interface Server {
  id: number;
  name: string;
  host: string;
  ssh_port: number;
  username: string;

  system_hostname: string | null;

  distribution: string | null;
  distribution_version: string | null;
  package_manager: string | null;
  architecture: string | null;
  kernel_version: string | null;

  reboot_required: boolean;
  cleanup_available: boolean | null;

  connection_status: string;
  updates_available: number;

  last_seen_at: string | null;
  updates_checked_at: string | null;
  last_check_at: string | null;
  last_error: string | null;

  created_at: string;
  updated_at: string;
}

export interface ScheduledTask {
  id: number;
  name: string;
  server_ids: number[];
  action: string;
  schedule_type: string;
  timezone: string;

  run_at: string | null;
  hour: number | null;
  minute: number | null;
  weekday: number | null;
  day_of_month: number | null;

  enabled: boolean;

  last_run_at: string | null;
  next_run_at: string | null;

  created_at: string;
  updated_at: string;
}

export interface HistoryEntry {
  id: number;
  server_ids: number[];
  server_name: string;
  action: string;
  status: string;
  package_count: number;
  reboot_required: boolean;
  message: string | null;
  created_at: string;
}

export interface PackageUpdate {
  name: string;
  installed_version: string;
  available_version: string;
  held?: boolean;
  locked?: boolean;
}

export interface UpdateResult {
  server_ids: number[];
  server: string;
  system_hostname: string | null;
  package_manager: string;
  updates_available: number;
  held_updates_available?: number;
  reboot_required: boolean;
  cleanup_available?: boolean;
  updates: PackageUpdate[];
  held_updates?: PackageUpdate[];
}

export interface InstallResult {
  server_ids: number[];
  server: string;
  system_hostname: string | null;
  installed_packages: string[];
  installed_count?: number;
  remaining_updates: number;
  reboot_required: boolean;
  updates?: PackageUpdate[];
  message?: string;
}

export interface CleanupResult {
  server_ids: number[];
  server: string;
  system_hostname: string | null;
  cleanup: Record<string, boolean>;
  remaining_updates: number;
  reboot_required: boolean;
}

export interface RebootReason {
  type: string;
  message: string;
  running_kernel?: string;
  installed_kernel?: string | null;
}

export interface RebootStatus {
  server_ids: number[];
  server: string;
  system_hostname: string | null;
  reboot_required: boolean;
  reboot_flag_present: boolean;
  running_kernel: string;
  newest_installed_kernel: string | null;
  newer_kernel_installed: boolean;
  reasons: RebootReason[];
}


export interface NotificationEventPreference {
  event_key: string;
  email_enabled: boolean;
  discord_enabled: boolean;
}


export interface NotificationSettings {
  email_enabled: boolean;
  smtp_host: string | null;
  smtp_port: number;
  smtp_security: "none" | "starttls" | "tls";
  smtp_username: string | null;
  smtp_password_configured: boolean;
  email_from: string | null;
  email_recipients: string[];

  discord_enabled: boolean;
  discord_webhook_configured: boolean;

  events: NotificationEventPreference[];
}


export interface NotificationSettingsUpdate {
  email_enabled: boolean;
  smtp_host: string | null;
  smtp_port: number;
  smtp_security: "none" | "starttls" | "tls";
  smtp_username: string | null;
  smtp_password?: string | null;
  email_from: string | null;
  email_recipients: string[];

  discord_enabled: boolean;
  discord_webhook_url?: string | null;

  events: NotificationEventPreference[];
}


export interface NotificationTestResult {
  channel: "email" | "discord";
  success: boolean;
}
