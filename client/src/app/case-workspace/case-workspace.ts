import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

type LegalCaseStatus = 'Action Required' | 'Pending' | 'Closed';
type PriorityRiskLevel = 'Low' | 'Medium' | 'High' | 'Critical';

interface LegalCaseDetail {
  id: string;
  caseNumber: string;
  status: LegalCaseStatus;
  assignedAttorney: string;
  createdDate: string;
  lastUpdatedDate: string;
  tags: string[];
  shortSummary: string;
  plaintiffName: string;
  compensationAmount: number;
  nextDueDate: string;
  externalLawFirmInvolved: string;
  courtInvolved: string;
  jurisdiction: string;
  caseType: string;
  priorityRiskLevel: PriorityRiskLevel;
  recent: boolean;
  lastCorrespondence: string;
  waitingFor: string;
}

interface TotoChatResponse {
  status: string;
  lastCorrespondence: string;
  waitingFor: string;
  summary: string;
}

interface ChatMessage {
  role: 'assistant' | 'user';
  text: string;
  response?: TotoChatResponse;
}

interface ChatConversation {
  id: string;
  title: string;
  subtitle: string;
  updatedAt: string;
  messages: ChatMessage[];
}

@Component({
  selector: 'app-case-workspace',
  imports: [CommonModule, CurrencyPipe, DatePipe, RouterLink],
  templateUrl: './case-workspace.html',
  styleUrl: './case-workspace.scss',
})
export class CaseWorkspaceComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly caseId = this.route.snapshot.paramMap.get('id') ?? '';
  private readonly caseApiUrl = `${this.apiOrigin}/api/v1/legal-cases/${this.caseId}`;
  private readonly totoApiUrl = `${this.apiOrigin}/api/v1/toto/chat`;

  readonly legalCase = signal<LegalCaseDetail | null>(null);
  readonly isLoading = signal(true);
  readonly errorMessage = signal('');
  readonly sidebarCollapsed = signal(false);
  readonly overviewHidden = signal(false);
  readonly totoDraft = signal('');
  readonly totoLoading = signal(false);
  readonly conversations = signal<ChatConversation[]>([]);
  readonly activeConversationId = signal('');
  readonly messages = computed(() => {
    const activeId = this.activeConversationId();
    return this.conversations().find((conversation) => conversation.id === activeId)?.messages ?? [];
  });

  readonly metadata = computed(() => {
    const legalCase = this.legalCase();
    if (!legalCase) {
      return [];
    }

    return [
      { label: 'Case number', value: legalCase.caseNumber },
      { label: 'Status', value: legalCase.status },
      { label: 'Assigned attorney', value: legalCase.assignedAttorney },
      { label: 'Created date', value: legalCase.createdDate, type: 'date' },
      { label: 'Last updated date', value: legalCase.lastUpdatedDate, type: 'date' },
      { label: 'Plaintiff name', value: legalCase.plaintiffName },
      { label: 'Compensation amount', value: legalCase.compensationAmount, type: 'currency' },
      { label: 'Next due date', value: legalCase.nextDueDate, type: 'date' },
      { label: 'External law firm involved', value: legalCase.externalLawFirmInvolved },
      { label: 'Court involved', value: legalCase.courtInvolved },
      { label: 'Jurisdiction', value: legalCase.jurisdiction },
      { label: 'Case type', value: legalCase.caseType },
      { label: 'Priority/risk level', value: legalCase.priorityRiskLevel },
    ];
  });

  ngOnInit(): void {
    this.http
      .get<LegalCaseDetail>(this.caseApiUrl)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: (legalCase) => {
          this.legalCase.set(legalCase);
          this.loadConversations(legalCase);
        },
        error: () => this.errorMessage.set('This case could not be loaded. Return to the dashboard and try again.'),
      });
  }

  toggleSidebar(): void {
    this.sidebarCollapsed.update((isCollapsed) => !isCollapsed);
  }

  hideOverview(): void {
    this.overviewHidden.set(true);
  }

  restoreOverview(): void {
    this.overviewHidden.set(false);
  }

  setTotoDraft(message: string): void {
    this.totoDraft.set(message);
  }

  sendTotoMessage(event: Event): void {
    event.preventDefault();
    const message = this.totoDraft().trim();
    if (!message || this.totoLoading()) {
      return;
    }

    this.totoDraft.set('');
    this.totoLoading.set(true);
    this.appendMessage({ role: 'user', text: message });

    this.http
      .post<TotoChatResponse>(this.totoApiUrl, { message, caseId: this.caseId })
      .pipe(finalize(() => this.totoLoading.set(false)))
      .subscribe({
        next: (response) => {
          this.appendMessage({ role: 'assistant', text: response.summary, response });
        },
        error: () => {
          this.appendMessage({
            role: 'assistant',
            text: 'Toto could not reach the case service. Please try again.',
          });
        },
      });
  }

  openConversation(conversationId: string): void {
    this.activeConversationId.set(conversationId);
  }

  riskClass(riskLevel: PriorityRiskLevel): string {
    return riskLevel.toLowerCase();
  }

  statusClass(status: LegalCaseStatus): string {
    return status.toLowerCase().replace(/\s+/g, '-');
  }

  private appendMessage(message: ChatMessage): void {
    const activeId = this.activeConversationId();
    this.conversations.update((conversations) =>
      conversations.map((conversation) =>
        conversation.id === activeId
          ? {
              ...conversation,
              subtitle: message.text,
              updatedAt: 'Just now',
              messages: [...conversation.messages, message],
            }
          : conversation,
      ),
    );
    this.persistConversations();
  }

  private loadConversations(legalCase: LegalCaseDetail): void {
    const savedConversations = this.readSavedConversations();
    const conversations = savedConversations.length
      ? savedConversations
      : this.buildSeedConversations(legalCase);

    this.conversations.set(conversations);
    this.activeConversationId.set(conversations[0]?.id ?? '');
    this.persistConversations();
  }

  private readSavedConversations(): ChatConversation[] {
    const rawConversations = window.localStorage.getItem(this.storageKey);
    if (!rawConversations) {
      return [];
    }

    try {
      const conversations = JSON.parse(rawConversations) as ChatConversation[];
      return Array.isArray(conversations) ? conversations : [];
    } catch {
      return [];
    }
  }

  private persistConversations(): void {
    window.localStorage.setItem(this.storageKey, JSON.stringify(this.conversations()));
  }

  private buildSeedConversations(legalCase: LegalCaseDetail): ChatConversation[] {
    return [
      {
        id: 'current-case-brief',
        title: 'Current case brief',
        subtitle: 'Status, owner, and immediate blocker',
        updatedAt: 'Today',
        messages: [
          {
            role: 'assistant',
            text: 'Hi, I’m Toto. Ask me anything about this case — status, correspondence, deadlines, risks, or next actions.',
          },
          {
            role: 'assistant',
            text: `${legalCase.caseNumber} is ${legalCase.status.toLowerCase()} and assigned to ${legalCase.assignedAttorney}. The next useful checkpoint is ${legalCase.waitingFor}`,
          },
        ],
      },
      {
        id: 'correspondence-review',
        title: 'Correspondence review',
        subtitle: 'Latest inbound note and response posture',
        updatedAt: 'Yesterday',
        messages: [
          {
            role: 'user',
            text: 'Summarize the latest correspondence and what we still need before responding.',
          },
          {
            role: 'assistant',
            text: `${legalCase.lastCorrespondence} The response should stay narrow, confirm receipt, and avoid committing to a settlement position until ${legalCase.assignedAttorney} has reviewed the record set.`,
          },
        ],
      },
      {
        id: 'deadline-risk-check',
        title: 'Deadline and risk check',
        subtitle: 'Due date, exposure, and priority level',
        updatedAt: 'Apr 24',
        messages: [
          {
            role: 'user',
            text: 'What is the timing risk on this matter?',
          },
          {
            role: 'assistant',
            text: `The next due date is ${new Date(legalCase.nextDueDate).toLocaleDateString()} and the priority level is ${legalCase.priorityRiskLevel}. The compensation amount currently tracked is ${new Intl.NumberFormat('en-US', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(legalCase.compensationAmount)}.`,
          },
        ],
      },
    ];
  }

  private get storageKey(): string {
    return `bussiesmw:toto-conversations:${this.caseId}`;
  }

  private get apiOrigin(): string {
    const hostname = window.location.hostname || 'localhost';
    return `http://${hostname}:8000`;
  }
}
