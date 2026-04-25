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

@Component({
  selector: 'app-root',
  imports: [CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${this.apiOrigin}/api/v1/legal-cases`;

  readonly cases = signal<LegalCase[]>([]);
  readonly activeFilter = signal<CaseFilter>('All');
  readonly activeRecentFilter = signal<RecentFilter>('all');
  readonly filtersOpen = signal(false);
  readonly searchQuery = signal('');
  readonly pageIndex = signal(0);
  readonly isLoading = signal(true);
  readonly errorMessage = signal('');
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

  setSearchQuery(query: string): void {
    this.searchQuery.set(query);
    this.pageIndex.set(0);
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
