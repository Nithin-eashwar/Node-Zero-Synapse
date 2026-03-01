import { Users, Search } from 'lucide-react';
import { useState, useMemo } from 'react';
import { useExpertForFile, useBusFactor } from '../lib/hooks';
import { LoadingState, ErrorState } from '../components/ui/StatusStates';

export default function SmartBlamePage() {
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedFile, setSelectedFile] = useState('');

    const expertQuery = useExpertForFile(selectedFile);
    const busFactorQuery = useBusFactor();

    // Build file list from bus factor data (these are the known modules)
    const fileList = useMemo(() => {
        const analysis = busFactorQuery.data?.analysis ?? {};
        return Object.entries(analysis).map(([filePath, busFactor]) => ({
            filePath,
            busFactor,
            isRisk: busFactor <= (busFactorQuery.data?.warning_threshold ?? 2),
        }));
    }, [busFactorQuery.data]);

    const filteredFiles = useMemo(() => {
        if (!searchQuery) return fileList;
        const q = searchQuery.toLowerCase();
        return fileList.filter(f => f.filePath.toLowerCase().includes(q));
    }, [fileList, searchQuery]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (searchQuery.trim()) {
            setSelectedFile(searchQuery.trim());
        }
    };

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/10">
                        <Users className="h-5 w-5 text-indigo-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold tracking-tight text-white">Smart Blame</h2>
                        <p className="text-xs text-neutral-500">
                            Find the true expert for any file — not just the last committer
                        </p>
                    </div>
                </div>
            </div>

            {/* File Search */}
            <form onSubmit={handleSearch} className="relative max-w-lg">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-600" />
                <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Enter a file path to find its expert (e.g. backend/api/main.py)"
                    className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] py-2.5 pl-10 pr-4 text-sm text-neutral-300 placeholder-neutral-600 outline-none transition-all focus:border-white/[0.12] focus:bg-white/[0.05]"
                />
            </form>

            {/* Expert Card (shows when a file is selected) */}
            {selectedFile && (
                <div className="rounded-2xl border border-indigo-500/10 bg-indigo-500/[0.03] p-6">
                    {expertQuery.isLoading && <LoadingState message={`Analyzing ${selectedFile}...`} />}
                    {expertQuery.isError && (
                        <ErrorState
                            title="Expert Analysis Failed"
                            message={`Could not analyze "${selectedFile}". Make sure the backend is running and the file exists in the repo.`}
                            onRetry={() => expertQuery.refetch()}
                        />
                    )}
                    {expertQuery.data && (
                        <div>
                            <h3 className="text-sm font-medium text-neutral-200 mb-4">
                                Expert for <span className="font-mono text-indigo-400">{expertQuery.data.target}</span>
                            </h3>
                            <div className="flex items-center gap-6">
                                {/* Primary Expert */}
                                {expertQuery.data.primary_expert ? (
                                    <div className="flex flex-col items-center gap-2">
                                        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-cyan-400 text-xl font-semibold text-white">
                                            {expertQuery.data.primary_expert.name
                                                .split(' ').map(w => w[0]).join('')}
                                        </div>
                                        <div className="text-center">
                                            <p className="text-sm font-medium text-white">
                                                {expertQuery.data.primary_expert.name}
                                            </p>
                                            <p className="text-[10px] text-neutral-600">
                                                {expertQuery.data.primary_expert.email}
                                            </p>
                                        </div>
                                    </div>
                                ) : (
                                    <p className="text-xs text-neutral-500">No expert found</p>
                                )}

                                {/* Metrics */}
                                <div className="flex-1 space-y-3">
                                    <div className="rounded-xl bg-indigo-500/[0.06] p-3">
                                        <p className="text-sm font-medium italic text-indigo-300/80">
                                            "{expertQuery.data.recommendation}"
                                        </p>
                                    </div>

                                    <div className="flex gap-4 text-xs">
                                        <div>
                                            <span className="text-neutral-500">Bus Factor: </span>
                                            <span className={`font-medium ${expertQuery.data.bus_factor <= 1 ? 'text-red-400' :
                                                    expertQuery.data.bus_factor <= 2 ? 'text-amber-400' :
                                                        'text-emerald-400'
                                                }`}>
                                                {expertQuery.data.bus_factor}
                                            </span>
                                        </div>
                                        {expertQuery.data.score && (
                                            <div>
                                                <span className="text-neutral-500">Score: </span>
                                                <span className="font-medium text-white">
                                                    {(expertQuery.data.score.total_score * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Score factors */}
                                    {expertQuery.data.score?.factors && (
                                        <div className="space-y-1.5">
                                            {Object.entries(expertQuery.data.score.factors).map(([key, value]) => (
                                                <div key={key} className="flex items-center gap-2">
                                                    <span className="w-32 text-right text-[11px] text-neutral-500">
                                                        {key.replace(/_/g, ' ')}
                                                    </span>
                                                    <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.04]">
                                                        <div
                                                            className="absolute inset-y-0 left-0 rounded-full bg-indigo-500"
                                                            style={{ width: `${Math.min(100, (value as number) * 100)}%` }}
                                                        />
                                                    </div>
                                                    <span className="w-10 text-right text-[11px] tabular-nums text-neutral-400">
                                                        {((value as number) * 100).toFixed(0)}%
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Secondary Experts */}
                            {expertQuery.data.secondary_experts.length > 0 && (
                                <div className="mt-4 border-t border-white/[0.06] pt-4">
                                    <h4 className="mb-2 text-xs font-medium text-neutral-500">
                                        Secondary Experts
                                    </h4>
                                    <div className="flex flex-wrap gap-2">
                                        {expertQuery.data.secondary_experts.map((se, i) => (
                                            <span key={i} className="rounded-full bg-white/[0.04] px-3 py-1 text-xs text-neutral-300">
                                                {se.developer.name}
                                                <span className="ml-1 text-neutral-600">
                                                    ({(se.score.total_score * 100).toFixed(0)}%)
                                                </span>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* File List Table */}
            <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6">
                <h3 className="mb-4 text-sm font-medium text-neutral-200">
                    Codebase Modules ({fileList.length})
                </h3>
                {busFactorQuery.isLoading ? (
                    <LoadingState message="Loading modules..." />
                ) : busFactorQuery.isError ? (
                    <ErrorState title="Modules Unavailable" onRetry={() => busFactorQuery.refetch()} />
                ) : (
                    <div className="overflow-hidden rounded-xl border border-white/[0.06]">
                        <table className="w-full text-left text-xs">
                            <thead>
                                <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                                    <th className="px-4 py-3 font-medium text-neutral-500">Module Path</th>
                                    <th className="px-4 py-3 font-medium text-neutral-500 text-center">Bus Factor</th>
                                    <th className="px-4 py-3 font-medium text-neutral-500">Risk</th>
                                    <th className="px-4 py-3 font-medium text-neutral-500">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredFiles.map((row) => (
                                    <tr
                                        key={row.filePath}
                                        className="border-b border-white/[0.04] transition-colors hover:bg-white/[0.03] cursor-pointer"
                                        onClick={() => setSelectedFile(row.filePath)}
                                    >
                                        <td className="px-4 py-3 font-mono text-neutral-300">{row.filePath}</td>
                                        <td className="px-4 py-3 text-center">
                                            <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${row.busFactor <= 1
                                                    ? 'bg-red-500/10 text-red-400'
                                                    : row.busFactor <= 2
                                                        ? 'bg-amber-500/10 text-amber-400'
                                                        : 'bg-emerald-500/10 text-emerald-400'
                                                }`}>
                                                {row.busFactor}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${row.isRisk
                                                    ? 'bg-red-500/10 text-red-400'
                                                    : 'bg-emerald-500/10 text-emerald-400'
                                                }`}>
                                                {row.isRisk ? 'AT RISK' : 'SAFE'}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <button
                                                className="text-indigo-400 hover:text-indigo-300 text-[11px]"
                                                onClick={(e) => { e.stopPropagation(); setSelectedFile(row.filePath); }}
                                            >
                                                Find Expert →
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                                {filteredFiles.length === 0 && (
                                    <tr>
                                        <td colSpan={4} className="px-4 py-8 text-center text-neutral-600">
                                            No modules found
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
