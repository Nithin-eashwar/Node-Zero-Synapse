import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, GitBranch, Code2, Network, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { WebGLShader } from '@/components/ui/web-gl-shader';
import { useUploadStatus } from '@/lib/hooks';

interface StepTiming {
    start: number | null;
    end: number | null;
}

const steps = [
    { key: 'cloning', label: 'Cloning repository', icon: GitBranch, color: 'indigo' },
    { key: 'parsing', label: 'Parsing codebase', icon: Code2, color: 'violet' },
    { key: 'building', label: 'Building dependency graph', icon: Network, color: 'emerald' },
];

function formatElapsed(seconds: number): string {
    if (seconds < 1) return '<1s';
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m ${s}s`;
}

function StepProgressBar({
    state,
    timing,
    elapsed,
    color,
}: {
    state: 'pending' | 'active' | 'done';
    timing?: StepTiming;
    elapsed: number;
    color: string;
}) {
    const duration = timing?.end && timing?.start ? timing.end - timing.start : 0;
    const colorMap: Record<string, { bar: string; bg: string; glow: string }> = {
        indigo: { bar: 'bg-indigo-500', bg: 'bg-indigo-500/20', glow: 'shadow-[0_0_12px_rgba(99,102,241,0.4)]' },
        violet: { bar: 'bg-violet-500', bg: 'bg-violet-500/20', glow: 'shadow-[0_0_12px_rgba(139,92,246,0.4)]' },
        emerald: { bar: 'bg-emerald-500', bg: 'bg-emerald-500/20', glow: 'shadow-[0_0_12px_rgba(52,211,153,0.4)]' },
    };
    const c = colorMap[color] || colorMap.indigo;

    if (state === 'pending') {
        return (
            <div className="mt-2">
                <div className="h-1.5 w-full rounded-full bg-white/[0.04]" />
            </div>
        );
    }

    if (state === 'done') {
        return (
            <div className="mt-2 flex items-center gap-2">
                <div className="h-1.5 flex-1 rounded-full bg-white/[0.06] overflow-hidden">
                    <motion.div
                        className={`h-full rounded-full ${c.bar}`}
                        initial={{ width: '80%' }}
                        animate={{ width: '100%' }}
                        transition={{ duration: 0.4, ease: 'easeOut' }}
                    />
                </div>
                <span className="text-[10px] font-medium text-white/30 tabular-nums min-w-[35px] text-right">
                    {formatElapsed(duration)}
                </span>
            </div>
        );
    }

    // Active — animated indeterminate + elapsed time
    return (
        <div className="mt-2 flex items-center gap-2">
            <div className={`h-1.5 flex-1 rounded-full ${c.bg} overflow-hidden relative`}>
                <motion.div
                    className={`absolute inset-y-0 left-0 rounded-full ${c.bar} ${c.glow}`}
                    initial={{ width: '5%', x: '0%' }}
                    animate={{
                        width: ['5%', '40%', '20%', '60%', '30%'],
                        x: ['0%', '30%', '50%', '20%', '60%'],
                    }}
                    transition={{
                        duration: 3,
                        repeat: Infinity,
                        ease: 'easeInOut',
                    }}
                />
            </div>
            <span className="text-[10px] font-medium text-white/40 tabular-nums min-w-[35px] text-right flex items-center gap-1">
                <Clock className="h-2.5 w-2.5" />
                {formatElapsed(elapsed)}
            </span>
        </div>
    );
}

export default function AnalyzingPage() {
    const navigate = useNavigate();
    const {
        data: status,
        isError: isStatusQueryError,
        error: statusQueryError,
        refetch: refetchStatus,
    } = useUploadStatus(true);
    const idleSinceRef = useRef<number | null>(null);
    const [tick, setTick] = useState(0);

    // Tick every second for live elapsed time
    useEffect(() => {
        const interval = setInterval(() => setTick((t) => t + 1), 1000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (status?.status === 'ready') {
            const timer = setTimeout(() => navigate('/dashboard'), 1500);
            return () => clearTimeout(timer);
        }
    }, [status?.status, navigate]);

    useEffect(() => {
        if (status?.status === 'idle') {
            if (idleSinceRef.current === null) {
                idleSinceRef.current = Date.now();
            }
            const idleMs = Date.now() - idleSinceRef.current;
            if (idleMs > 5000) {
                navigate('/');
            }
        } else {
            idleSinceRef.current = null;
        }
    }, [status?.status, navigate]);

    const currentStatus = status?.status ?? 'idle';
    const repoName = status?.repo_name ?? 'repository';
    const isError = currentStatus === 'error' || isStatusQueryError;
    const isReady = currentStatus === 'ready';
    const progress = status?.progress ?? 0;
    const stepTimes = (status?.step_times ?? {}) as Record<string, StepTiming>;
    const queryErrorMessage =
        statusQueryError instanceof Error
            ? statusQueryError.message
            : 'Unable to fetch analysis status from backend.';
    const displayError = currentStatus === 'error' ? status?.error : queryErrorMessage;

    const getStepState = (stepKey: string): 'pending' | 'active' | 'done' => {
        const order = ['cloning', 'parsing', 'building'];
        const currentIdx = order.indexOf(currentStatus);
        const stepIdx = order.indexOf(stepKey);
        if (isReady) return 'done';
        if (stepIdx < currentIdx) return 'done';
        if (stepIdx === currentIdx) return 'active';
        return 'pending';
    };

    const getElapsed = (stepKey: string): number => {
        const t = stepTimes[stepKey];
        if (!t?.start) return 0;
        if (t.end) return t.end - t.start;
        return Date.now() / 1000 - t.start;
    };

    // Suppress lint warning for tick
    void tick;

    return (
        <div className="relative flex min-h-screen w-full flex-col items-center justify-center overflow-hidden">
            <WebGLShader />
            <div className="relative z-10 w-full max-w-lg px-4">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="rounded-2xl border border-white/[0.08] bg-black/60 p-8 backdrop-blur-xl"
                >
                    {/* Header */}
                    <div className="mb-6 text-center">
                        <motion.div
                            animate={{ rotate: isReady ? 0 : 360 }}
                            transition={{ duration: 2, repeat: isReady ? 0 : Infinity, ease: 'linear' }}
                            className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-white/10 bg-white/5"
                        >
                            {isError ? (
                                <XCircle className="h-7 w-7 text-red-400" />
                            ) : isReady ? (
                                <CheckCircle2 className="h-7 w-7 text-green-400" />
                            ) : (
                                <Loader2 className="h-7 w-7 text-indigo-400" />
                            )}
                        </motion.div>
                        <h2 className="text-xl font-semibold text-white">
                            {isError ? 'Analysis Failed' : isReady ? 'Analysis Complete!' : 'Analyzing Codebase'}
                        </h2>
                        <p className="mt-1 text-sm text-white/40">
                            {isError
                                ? displayError
                                : isReady
                                    ? 'Redirecting to dashboard...'
                                    : currentStatus === 'idle'
                                        ? 'Waiting for analysis job to start...'
                                        : repoName}
                        </p>
                    </div>

                    {/* Overall progress bar */}
                    {!isError && (
                        <div className="mb-6">
                            <div className="flex items-center justify-between mb-1.5">
                                <span className="text-[11px] font-medium text-white/30">Overall Progress</span>
                                <span className="text-[11px] font-semibold text-white/50 tabular-nums">{progress}%</span>
                            </div>
                            <div className="h-2 w-full rounded-full bg-white/[0.06] overflow-hidden">
                                <motion.div
                                    className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-violet-500 to-emerald-500"
                                    initial={{ width: '0%' }}
                                    animate={{ width: `${progress}%` }}
                                    transition={{ duration: 0.6, ease: 'easeOut' }}
                                    style={{
                                        boxShadow: '0 0 16px rgba(99, 102, 241, 0.4), 0 0 32px rgba(139, 92, 246, 0.2)',
                                    }}
                                />
                            </div>
                        </div>
                    )}

                    {/* Steps */}
                    {!isError && (
                        <div className="space-y-3">
                            {steps.map((step, i) => {
                                const state = getStepState(step.key);
                                const Icon = step.icon;
                                const elapsed = getElapsed(step.key);
                                return (
                                    <motion.div
                                        key={step.key}
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.1, duration: 0.3 }}
                                        className={`rounded-xl px-4 py-3 transition-all duration-300 ${state === 'active'
                                            ? 'border border-indigo-500/30 bg-indigo-500/10'
                                            : state === 'done'
                                                ? 'border border-green-500/20 bg-green-500/5'
                                                : 'border border-white/[0.04] bg-white/[0.02]'
                                            }`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div
                                                className={`flex h-8 w-8 items-center justify-center rounded-lg ${state === 'active'
                                                    ? 'bg-indigo-500/20'
                                                    : state === 'done'
                                                        ? 'bg-green-500/20'
                                                        : 'bg-white/5'
                                                    }`}
                                            >
                                                {state === 'done' ? (
                                                    <CheckCircle2 className="h-4 w-4 text-green-400" />
                                                ) : state === 'active' ? (
                                                    <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />
                                                ) : (
                                                    <Icon className="h-4 w-4 text-white/30" />
                                                )}
                                            </div>
                                            <div className="flex-1">
                                                <span
                                                    className={`text-sm font-medium ${state === 'active'
                                                        ? 'text-indigo-300'
                                                        : state === 'done'
                                                            ? 'text-green-300'
                                                            : 'text-white/30'
                                                        }`}
                                                >
                                                    {state === 'done' ? step.label.replace('...', '') + ' ✓' : step.label + '...'}
                                                </span>
                                            </div>
                                        </div>
                                        <StepProgressBar
                                            state={state}
                                            timing={stepTimes[step.key]}
                                            elapsed={elapsed}
                                            color={step.color}
                                        />
                                    </motion.div>
                                );
                            })}
                        </div>
                    )}

                    {/* Stats (when ready) */}
                    <AnimatePresence>
                        {isReady && status?.stats && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                transition={{ delay: 0.3 }}
                                className="mt-6 grid grid-cols-2 gap-3"
                            >
                                {[
                                    { label: 'Files', value: status.stats.files },
                                    { label: 'Entities', value: status.stats.entities },
                                    { label: 'Nodes', value: status.stats.nodes },
                                    { label: 'Edges', value: status.stats.edges },
                                ].map((s) => (
                                    <div
                                        key={s.label}
                                        className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-center"
                                    >
                                        <div className="text-lg font-semibold text-white">{s.value}</div>
                                        <div className="text-[11px] text-white/40">{s.label}</div>
                                    </div>
                                ))}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Error retry */}
                    {isError && (
                        <div className="mt-6 text-center">
                            <p className="mb-4 text-sm text-red-300/70">{displayError}</p>
                            <div className="flex items-center justify-center gap-3">
                                <button
                                    onClick={() => {
                                        if (isStatusQueryError) {
                                            void refetchStatus();
                                            return;
                                        }
                                        navigate('/');
                                    }}
                                    className="rounded-full border border-white/15 bg-white/5 px-6 py-2 text-sm font-medium text-white transition-all hover:bg-white/10"
                                >
                                    {isStatusQueryError ? 'Retry Status Check' : 'Try Again'}
                                </button>
                                <button
                                    onClick={() => navigate('/')}
                                    className="rounded-full border border-white/15 bg-white/5 px-6 py-2 text-sm font-medium text-white transition-all hover:bg-white/10"
                                >
                                    Back Home
                                </button>
                            </div>
                        </div>
                    )}
                </motion.div>
            </div>
        </div>
    );
}
