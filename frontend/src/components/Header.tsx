import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { statsApi } from '../api';
import './Header.css';

function formatRelative(iso: string | null): string {
  if (!iso) return '未同期';
  // SQLiteのCURRENT_TIMESTAMPはUTC。'Z'を補ってパースする
  const normalized = iso.includes('T') ? iso : iso.replace(' ', 'T') + 'Z';
  const then = new Date(normalized);
  if (isNaN(then.getTime())) return iso;
  const diffMs = Date.now() - then.getTime();
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return 'たった今';
  if (min < 60) return `${min}分前`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}時間前`;
  const day = Math.floor(hr / 24);
  return `${day}日前`;
}

export function Header() {
  const queryClient = useQueryClient();

  const { data: syncStatus } = useQuery({
    queryKey: ['syncStatus'],
    queryFn: async () => (await statsApi.getSyncStatus()).data,
    staleTime: 60 * 1000,
  });

  const syncMutation = useMutation({
    mutationFn: async () => (await statsApi.syncDatabase()).data,
    onSuccess: () => {
      // 同期後は全データ系クエリを無効化して最新を反映
      queryClient.invalidateQueries();
    },
  });

  const staleDays = (() => {
    if (!syncStatus?.last_sync) return null;
    const normalized = syncStatus.last_sync.includes('T')
      ? syncStatus.last_sync
      : syncStatus.last_sync.replace(' ', 'T') + 'Z';
    const then = new Date(normalized);
    if (isNaN(then.getTime())) return null;
    return (Date.now() - then.getTime()) / 86400000;
  })();
  const isStale = staleDays !== null && staleDays >= 1;

  return (
    <header className="app-header">
      <h1 className="app-header-title">Claude Code Analytics</h1>
      <div className="app-header-right">
        <div className="sync-info">
          <span className={`sync-time ${isStale ? 'stale' : ''}`}>
            最終同期: {formatRelative(syncStatus?.last_sync ?? null)}
          </span>
          {syncStatus?.latest_data_date && (
            <span className="sync-latest">データ最新日: {syncStatus.latest_data_date}</span>
          )}
        </div>
        <button
          className="sync-button"
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? '同期中...' : 'データを同期'}
        </button>
      </div>
    </header>
  );
}
