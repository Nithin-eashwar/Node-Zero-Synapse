import { Loader2, WifiOff } from 'lucide-react';

interface LoadingStateProps {
    message?: string;
}

export function LoadingState({ message = 'Loading data...' }: LoadingStateProps) {
    return (
        <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-neutral-600" />
            <p className="mt-3 text-sm text-neutral-600">{message}</p>
        </div>
    );
}

interface ErrorStateProps {
    title?: string;
    message?: string;
    onRetry?: () => void;
}

export function ErrorState({
    title = 'Connection Error',
    message = 'Could not reach the backend. Make sure the API server is running.',
    onRetry,
}: ErrorStateProps) {
    return (
        <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-red-500/10">
                <WifiOff className="h-7 w-7 text-red-400" />
            </div>
            <h3 className="text-sm font-medium text-neutral-200">{title}</h3>
            <p className="mt-2 max-w-sm text-xs text-neutral-500">{message}</p>
            {onRetry && (
                <button
                    onClick={onRetry}
                    className="mt-4 rounded-lg border border-white/[0.06] bg-white/[0.04] px-4 py-2 text-xs font-medium text-neutral-300 transition-all hover:bg-white/[0.08]"
                >
                    Retry
                </button>
            )}
        </div>
    );
}

export function EmptyState({ message = 'No data available' }: { message?: string }) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-sm text-neutral-600">{message}</p>
        </div>
    );
}
