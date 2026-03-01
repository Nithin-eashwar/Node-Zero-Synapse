import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import { useDrift } from '../../lib/hooks';
import { LoadingState, ErrorState } from '../ui/StatusStates';

export default function DriftChart() {
    const { data, isLoading, isError, refetch } = useDrift();

    if (isLoading) return (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
            <LoadingState message="Loading drift data..." />
        </div>
    );
    if (isError) return (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
            <ErrorState title="Drift Data Unavailable" message="Backend governance endpoint not reachable." onRetry={() => refetch()} />
        </div>
    );

    // Build chart data from drift response
    const current = data?.current;
    const baseline = data?.baseline;
    const driftScore = data?.drift_score ?? 0;

    // Create a simple chart with current vs baseline metrics
    const chartData = [
        { label: 'Coupling', current: current?.coupling_score ?? 0, baseline: baseline?.coupling_score ?? 0 },
        { label: 'Cohesion', current: current?.cohesion_score ?? 0, baseline: baseline?.cohesion_score ?? 0 },
    ];

    // If we have layer balance data, add it
    if (current?.layer_balance) {
        Object.entries(current.layer_balance).forEach(([layer, val]) => {
            chartData.push({
                label: layer,
                current: val,
                baseline: baseline?.layer_balance?.[layer] ?? val,
            });
        });
    }

    return (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
            <div className="mb-4 flex items-center justify-between">
                <div>
                    <h3 className="text-sm font-medium text-neutral-200">Architectural Health</h3>
                    <p className="text-[11px] text-neutral-600">Current drift analysis</p>
                </div>
                <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-medium ${driftScore > 0.5 ? 'bg-red-500/10 text-red-400' :
                        driftScore > 0.2 ? 'bg-amber-500/10 text-amber-400' :
                            'bg-emerald-500/10 text-emerald-400'
                    }`}>
                    {driftScore > 0.5 ? '⚠ High Drift' : driftScore > 0.2 ? '↑ Moderate Drift' : '✓ Stable'}
                </span>
            </div>

            <div className="mb-4 grid grid-cols-3 gap-3">
                <div className="rounded-xl bg-white/[0.02] p-3 text-center">
                    <div className="text-lg font-semibold tabular-nums text-white">{(current?.coupling_score ?? 0).toFixed(2)}</div>
                    <div className="text-[10px] text-neutral-600">Coupling</div>
                </div>
                <div className="rounded-xl bg-white/[0.02] p-3 text-center">
                    <div className="text-lg font-semibold tabular-nums text-white">{(current?.cohesion_score ?? 0).toFixed(2)}</div>
                    <div className="text-[10px] text-neutral-600">Cohesion</div>
                </div>
                <div className="rounded-xl bg-white/[0.02] p-3 text-center">
                    <div className="text-lg font-semibold tabular-nums text-white">{current?.violation_count ?? 0}</div>
                    <div className="text-[10px] text-neutral-600">Violations</div>
                </div>
            </div>

            <ResponsiveContainer width="100%" height={160}>
                <AreaChart data={chartData}>
                    <defs>
                        <linearGradient id="currentGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#818cf8" stopOpacity={0.2} />
                            <stop offset="95%" stopColor="#818cf8" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
                    <XAxis
                        dataKey="label"
                        tick={{ fill: '#525252', fontSize: 10 }}
                        tickLine={false}
                        axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                    />
                    <YAxis
                        tick={{ fill: '#525252', fontSize: 10 }}
                        tickLine={false}
                        axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                        domain={[0, 1]}
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: '#0a0a0a',
                            border: '1px solid rgba(255,255,255,0.08)',
                            borderRadius: '0.75rem',
                            fontSize: '11px',
                            color: '#d4d4d4',
                        }}
                    />
                    <Area
                        type="monotone"
                        dataKey="current"
                        stroke="#818cf8"
                        fill="url(#currentGrad)"
                        strokeWidth={1.5}
                        dot={false}
                        name="Current"
                    />
                    <Area
                        type="monotone"
                        dataKey="baseline"
                        stroke="#525252"
                        fill="transparent"
                        strokeWidth={1}
                        strokeDasharray="4 4"
                        dot={false}
                        name="Baseline"
                    />
                </AreaChart>
            </ResponsiveContainer>

            {/* Recommendations */}
            {data?.recommendations && data.recommendations.length > 0 && (
                <div className="mt-4 space-y-1">
                    <h4 className="text-[11px] font-medium text-neutral-500">Recommendations</h4>
                    {data.recommendations.slice(0, 3).map((r, i) => (
                        <p key={i} className="text-[11px] text-neutral-600">• {r}</p>
                    ))}
                </div>
            )}
        </div>
    );
}
