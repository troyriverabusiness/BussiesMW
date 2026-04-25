import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';

type LegalCaseStatus = 'Action Required' | 'Pending' | 'Closed';
type CaseFilter = 'All' | LegalCaseStatus;
type RecentFilter = 'all' | 'recent' | 'nonRecent';

interface LegalCase {
  id: string;
  type: string;
  issueSummary: string;
  status: LegalCaseStatus;
  lastUpdated: string;
  recent: boolean;
}

interface TotoChatResponse {
  status: string;
  lastCorrespondence: string;
  waitingFor: string;
  summary: string;
}

interface TotoMessage {
  role: 'user' | 'assistant';
  text: string;
  caseId?: string;
  response?: TotoChatResponse;
}

@Component({
  selector: 'app-root',
  imports: [CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${this.apiOrigin}/api/v1/legal-cases`;
  private readonly totoApiUrl = `${this.apiOrigin}/api/v1/toto/chat`;

  readonly cases = signal<LegalCase[]>([]);
  readonly activeFilter = signal<CaseFilter>('All');
  readonly activeRecentFilter = signal<RecentFilter>('all');
  readonly filtersOpen = signal(false);
  readonly searchQuery = signal('');
  readonly pageIndex = signal(0);
  readonly isLoading = signal(true);
  readonly errorMessage = signal('');
  readonly totoOpen = signal(false);
  readonly totoLoading = signal(false);
  readonly totoMuted = signal(false);
  readonly totoDraft = signal('');
  readonly totoMessages = signal<TotoMessage[]>([
    {
      role: 'assistant',
      text: 'I am Toto. Ask for a case update or use a row action to brief me with the internal case ID.',
    },
  ]);
  readonly filters: CaseFilter[] = ['All', 'Action Required', 'Pending', 'Closed'];
  readonly recentFilters: Array<{ label: string; value: RecentFilter }> = [
    { label: 'All cases', value: 'all' },
    { label: 'Recent only', value: 'recent' },
    { label: 'Non-recent only', value: 'nonRecent' },
  ];
  readonly pageSize = 10;

  readonly filteredCases = computed(() => {
    const filter = this.activeFilter();
    const recentFilter = this.activeRecentFilter();
    const query = this.searchQuery().trim().toLowerCase();
    const filtered = this.cases().filter((legalCase) => {
      const matchesFilter = filter === 'All' || legalCase.status === filter;
      const matchesRecentFilter =
        recentFilter === 'all' ||
        (recentFilter === 'recent' && legalCase.recent) ||
        (recentFilter === 'nonRecent' && !legalCase.recent);
      const searchableText = [
        legalCase.id,
        legalCase.type,
        legalCase.issueSummary,
        legalCase.status,
      ]
        .join(' ')
        .toLowerCase();

      return matchesFilter && matchesRecentFilter && (!query || searchableText.includes(query));
    });

    return [...filtered].sort((firstCase, secondCase) => {
      const firstDate = new Date(firstCase.lastUpdated).getTime();
      const secondDate = new Date(secondCase.lastUpdated).getTime();
      return secondDate - firstDate;
    });
  });

  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.filteredCases().length / this.pageSize)));
  readonly paginatedCases = computed(() => {
    const start = this.pageIndex() * this.pageSize;
    return this.filteredCases().slice(start, start + this.pageSize);
  });

  ngOnInit(): void {
    this.http
      .get<LegalCase[]>(this.apiUrl)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: (cases) => {
          this.cases.set(cases);
        },
        error: () => {
          this.errorMessage.set('Case data is unavailable. Verify that the FastAPI service is running.');
        },
      });
  }

  setFilter(filter: CaseFilter): void {
    this.activeFilter.set(filter);
    this.pageIndex.set(0);
  }

  setRecentFilter(filter: RecentFilter): void {
    this.activeRecentFilter.set(filter);
    this.pageIndex.set(0);
  }

  toggleFilters(): void {
    this.filtersOpen.update((isOpen) => !isOpen);
  }

  toggleToto(): void {
    this.totoOpen.update((isOpen) => !isOpen);
    this.playTone(520, 0.035);
  }

  toggleTotoMute(): void {
    this.totoMuted.update((isMuted) => !isMuted);
  }

  setSearchQuery(query: string): void {
    this.searchQuery.set(query);
    this.pageIndex.set(0);
  }

  setTotoDraft(message: string): void {
    this.totoDraft.set(message);
  }

  sendTotoDraft(event: Event): void {
    event.preventDefault();
    const request = this.totoDraft().trim();
    if (!request || this.totoLoading()) {
      return;
    }

    this.totoDraft.set('');
    this.sendTotoRequest(request);
  }

  requestCaseUpdate(legalCase: LegalCase, event: Event): void {
    event.stopPropagation();
    this.totoOpen.set(true);
    this.sendTotoRequest('Give me an update on this case.', legalCase.id);
  }

  nextPage(): void {
    this.pageIndex.update((index) => Math.min(index + 1, this.totalPages() - 1));
  }

  previousPage(): void {
    this.pageIndex.update((index) => Math.max(index - 1, 0));
  }

  openCase(legalCase: LegalCase): void {
    // Keeps backend identifiers internal while preserving a concrete row action hook.
    console.info('Open legal case', legalCase.id);
  }

  private sendTotoRequest(request: string, caseId?: string): void {
    this.totoLoading.set(true);
    this.totoMessages.update((messages) => [...messages, { role: 'user', text: request, caseId }]);
    this.playTone(440, 0.025);

    this.http
      .post<TotoChatResponse>(this.totoApiUrl, { request, caseId })
      .pipe(finalize(() => this.totoLoading.set(false)))
      .subscribe({
        next: (response) => {
          this.totoMessages.update((messages) => [
            ...messages,
            {
              role: 'assistant',
              text: response.summary,
              response,
            },
          ]);
          this.playTone(660, 0.04);
        },
        error: () => {
          this.totoMessages.update((messages) => [
            ...messages,
            {
              role: 'assistant',
              text: 'Toto could not reach the case-update service. Please try again.',
            },
          ]);
        },
      });
  }

  private playTone(frequency: number, duration: number): void {
    if (this.totoMuted()) {
      return;
    }

    const AudioContextClass =
      window.AudioContext ||
      (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) {
      return;
    }

    const audioContext = new AudioContextClass();
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();

    oscillator.frequency.value = frequency;
    oscillator.type = 'sine';
    gain.gain.value = 0.018;
    oscillator.connect(gain);
    gain.connect(audioContext.destination);
    oscillator.start();
    oscillator.stop(audioContext.currentTime + duration);
    oscillator.onended = () => audioContext.close();
  }

  filterCount(filter: CaseFilter): number {
    if (filter === 'All') {
      return this.cases().length;
    }

    return this.cases().filter((legalCase) => legalCase.status === filter).length;
  }

  recentFilterCount(filter: RecentFilter): number {
    if (filter === 'all') {
      return this.cases().length;
    }

    return this.cases().filter((legalCase) => (filter === 'recent' ? legalCase.recent : !legalCase.recent)).length;
  }

  statusClass(status: LegalCaseStatus): string {
    return status.toLowerCase().replace(/\s+/g, '-');
  }

  trackCase(_: number, legalCase: LegalCase): string {
    return legalCase.id;
  }

  private get apiOrigin(): string {
    const hostname = window.location.hostname || 'localhost';
    return `http://${hostname}:8000`;
  }
}
