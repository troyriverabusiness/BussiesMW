import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

interface JsonEntry {
  key: string;
  label: string;
  value: unknown;
}

interface DisplayRow {
  label: string;
  value: string;
}

interface RawEmailView {
  subject: string;
  from: string;
  receivedAt: string;
  messageId: string;
  body: string;
}

@Component({
  selector: 'app-trace-json-viewer',
  imports: [CommonModule],
  templateUrl: './trace-json-viewer.component.html',
  styleUrl: './trace-json-viewer.component.scss',
})
export class TraceJsonViewerComponent {
  @Input() title = 'Trace data';
  @Input() set data(value: unknown) {
    this.value = this.parseJsonString(value);
  }

  protected value: unknown = null;

  protected hasKnownSections(): boolean {
    return Boolean(this.rawEmail() || this.issueOutput() || this.departmentValidation());
  }

  protected rawEmail(): RawEmailView | null {
    const rawEmail = this.knownRecord('raw_email');
    if (!rawEmail) {
      return null;
    }

    return {
      subject: this.textField(rawEmail, ['subject', 'email_subject']) || 'No subject',
      from: this.textField(rawEmail, ['from', 'sender', 'sender_email', 'from_email']) || 'Sender not specified',
      receivedAt:
        this.textField(rawEmail, ['received_at', 'receivedAt', 'date', 'timestamp']) || 'Received time not specified',
      messageId:
        this.textField(rawEmail, ['message_id', 'messageId', 'id']) || 'Message ID not available',
      body: this.textField(rawEmail, ['body', 'text', 'content', 'message']) || 'No email body available.',
    };
  }

  protected issueOutput(): Record<string, unknown> | null {
    return this.knownRecord('issue_output');
  }

  protected departmentValidation(): Record<string, unknown> | null {
    return this.knownRecord('department_validation');
  }

  protected listItems(record: Record<string, unknown>, key: string): string[] {
    const value = record[key];
    if (Array.isArray(value)) {
      return value.map((item) => this.displayValue(item)).filter(Boolean);
    }
    if (typeof value === 'string' && value.trim()) {
      return [value.trim()];
    }
    return [];
  }

  protected sopFlags(record: Record<string, unknown>): string[] {
    return this.listItems(record, 'sop_flags');
  }

  protected issueCaseFieldRows(record: Record<string, unknown>): DisplayRow[] {
    const caseFields = this.asRecord(record['case_fields']);
    if (!caseFields) {
      return [];
    }

    return [
      this.row(caseFields, 'Status', ['status']),
      this.row(caseFields, 'Priority', ['priority', 'risk_level', 'priority_risk_level']),
      this.row(caseFields, 'Next due date', ['next_due_date', 'nextDueDate']),
      this.row(caseFields, 'Information gaps', ['information_gaps', 'informationGaps']),
      this.row(caseFields, 'Suggested action items', ['suggested_action_items', 'suggestionActionItems']),
    ].filter((item): item is DisplayRow => Boolean(item));
  }

  protected escalationRows(record: Record<string, unknown>): DisplayRow[] {
    const escalation = this.asRecord(record['escalation']) ?? record;
    return [
      this.row(escalation, 'Escalation reason', ['escalation_reason', 'reason']),
      this.row(escalation, 'Escalation target', ['escalation_target', 'target']),
      this.row(escalation, 'Internal escalation required', [
        'requires_internal_escalation',
        'requiresInternalEscalation',
      ]),
    ].filter((item): item is DisplayRow => Boolean(item));
  }

  protected completenessScore(record: Record<string, unknown>): number | null {
    const escalation = this.asRecord(record['escalation']) ?? record;
    const value = this.firstValue(escalation, ['completeness_score', 'completenessScore']);
    if (typeof value === 'number' && Number.isFinite(value)) {
      return Math.round(value <= 1 ? value * 100 : value);
    }
    if (typeof value === 'string') {
      const parsed = Number(value.replace('%', '').trim());
      return Number.isFinite(parsed) ? Math.round(parsed <= 1 ? parsed * 100 : parsed) : null;
    }
    return null;
  }

  protected validationBadge(record: Record<string, unknown>): string {
    return this.asBoolean(this.firstValue(record, ['validated', 'is_valid', 'valid'])) ? 'Validated' : 'Not validated';
  }

  protected validationClass(record: Record<string, unknown>): string {
    return this.asBoolean(this.firstValue(record, ['validated', 'is_valid', 'valid'])) ? 'positive' : 'attention';
  }

  protected validationReason(record: Record<string, unknown>): string {
    return this.textField(record, ['reason', 'validation_reason']) || 'No validation reason provided.';
  }

  protected validationConcerns(record: Record<string, unknown>): string[] {
    return this.listItems(record, 'concerns');
  }

  protected validationCaseFieldRows(record: Record<string, unknown>): DisplayRow[] {
    const caseFields = this.asRecord(record['case_fields']) ?? record;
    return [
      this.row(caseFields, 'Internal', ['internal']),
      this.row(caseFields, 'Department', ['department']),
      this.row(caseFields, 'Legal issue', ['legal_issue', 'legalIssue']),
      this.row(caseFields, 'Jurisdiction', ['jurisdiction']),
      this.row(caseFields, 'Court authority', ['court_authority', 'courtAuthority']),
      this.row(caseFields, 'Redirect target', ['redirect_target', 'redirectTarget']),
    ].filter((item): item is DisplayRow => Boolean(item));
  }

  protected objectEntries(value: unknown): JsonEntry[] {
    const record = this.asRecord(value);
    if (!record) {
      return [];
    }
    return Object.entries(record).map(([key, entryValue]) => ({
      key,
      label: this.humanize(key),
      value: entryValue,
    }));
  }

  protected arrayItems(value: unknown): unknown[] {
    return Array.isArray(value) ? value : [];
  }

  protected isRecord(value: unknown): value is Record<string, unknown> {
    return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
  }

  protected isArray(value: unknown): value is unknown[] {
    return Array.isArray(value);
  }

  protected isPrimitive(value: unknown): boolean {
    return !this.isRecord(value) && !Array.isArray(value);
  }

  protected displayValue(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'Not specified';
    }
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    if (typeof value === 'number') {
      return String(value);
    }
    if (typeof value === 'string') {
      return value;
    }
    if (Array.isArray(value)) {
      return value.map((item) => this.displayValue(item)).join(', ');
    }
    return this.formatJson(value);
  }

  protected preview(value: unknown): string {
    if (Array.isArray(value)) {
      return `${value.length} item${value.length === 1 ? '' : 's'}`;
    }
    const record = this.asRecord(value);
    if (record) {
      const count = Object.keys(record).length;
      return `${count} field${count === 1 ? '' : 's'}`;
    }
    return this.displayValue(value);
  }

  protected humanize(key: string): string {
    return key
      .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
      .replace(/[_-]+/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  private knownRecord(key: string): Record<string, unknown> | null {
    const root = this.asRecord(this.value);
    if (!root) {
      return null;
    }
    return this.asRecord(root[key]);
  }

  private parseJsonString(value: unknown): unknown {
    if (typeof value !== 'string') {
      return value;
    }
    const trimmed = value.trim();
    if (!trimmed || !/^[\[{]/.test(trimmed)) {
      return value;
    }
    try {
      return JSON.parse(trimmed) as unknown;
    } catch {
      return value;
    }
  }

  private formatJson(value: unknown): string {
    if (typeof value === 'string') {
      return value;
    }
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }

  private asRecord(value: unknown): Record<string, unknown> | null {
    return this.isRecord(value) ? value : null;
  }

  private row(record: Record<string, unknown>, label: string, keys: string[]): DisplayRow | null {
    const value = this.firstValue(record, keys);
    if (value === null || value === undefined || value === '') {
      return null;
    }
    return { label, value: this.displayValue(value) };
  }

  private textField(record: Record<string, unknown>, keys: string[]): string {
    const value = this.firstValue(record, keys);
    if (value === null || value === undefined || value === '') {
      return '';
    }
    return typeof value === 'string' ? value.trim() : this.displayValue(value);
  }

  private firstValue(record: Record<string, unknown>, keys: string[]): unknown {
    for (const key of keys) {
      if (key in record) {
        return record[key];
      }
    }
    return null;
  }

  private asBoolean(value: unknown): boolean {
    if (typeof value === 'boolean') {
      return value;
    }
    if (typeof value === 'string') {
      return ['true', 'yes', 'validated', 'valid'].includes(value.trim().toLowerCase());
    }
    return Boolean(value);
  }
}
