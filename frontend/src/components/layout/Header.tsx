import { Search, Bell, Settings } from 'lucide-react';

export default function Header() {
    return (
        <header className="fixed left-16 right-0 top-0 z-40 flex h-14 items-center justify-between border-b border-white/[0.06] bg-black/80 px-6 backdrop-blur-2xl">
            {/* Branding */}
            <div className="flex items-center gap-3">
                <h1 className="text-sm font-semibold tracking-wide text-white">
                    SYNAPSE
                </h1>
                <span className="rounded-full bg-white/[0.06] px-2 py-0.5 text-[10px] font-medium tracking-wider text-neutral-500">
                    GRAPHRAG
                </span>
            </div>

            {/* Search Bar */}
            <div className="relative flex w-full max-w-md items-center">
                <Search className="absolute left-3 h-4 w-4 text-neutral-600" />
                <input
                    type="text"
                    placeholder="Search codebase..."
                    className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] py-2 pl-10 pr-4 text-sm text-neutral-300 placeholder-neutral-600 outline-none transition-all focus:border-white/[0.12] focus:bg-white/[0.05]"
                />
                <kbd className="absolute right-3 rounded border border-white/[0.08] bg-white/[0.04] px-1.5 py-0.5 text-[10px] font-medium text-neutral-600">
                    ⌘K
                </kbd>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1">
                <button className="relative flex h-9 w-9 items-center justify-center rounded-xl text-neutral-600 transition-colors hover:bg-white/[0.04] hover:text-neutral-400">
                    <Bell className="h-4 w-4" />
                    <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500" />
                </button>
                <button className="flex h-9 w-9 items-center justify-center rounded-xl text-neutral-600 transition-colors hover:bg-white/[0.04] hover:text-neutral-400">
                    <Settings className="h-4 w-4" />
                </button>
            </div>
        </header>
    );
}
