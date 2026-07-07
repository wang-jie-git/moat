import * as vscode from 'vscode';
import * as path from 'path';
import axios, { AxiosInstance } from 'axios';

export function activate(context: vscode.ExtensionContext) {
    console.log('Moat extension is now active!');

    const config = vscode.workspace.getConfiguration('moat');
    const sidecarPort = config.get<number>('sidecar.port', 9877);
    const moatPath = config.get<string>('path', 'moat');

    // Create API client
    const api: AxiosInstance = axios.create({
        baseURL: `http://localhost:${sidecarPort}`,
        timeout: 10000,
    });

    // Register commands
    let disposable;

    disposable = vscode.commands.registerCommand('moat.check', async () => {
        await runMoatCheck(api, moatPath);
    });

    context.subscriptions.push(disposable);

    disposable = vscode.commands.registerCommand('moat.fix', async () => {
        await showMoatFix(api, moatPath);
    });

    context.subscriptions.push(disposable);

    disposable = vscode.commands.registerCommand('moat.init', async () => {
        await runMoatInit(moatPath);
    });

    context.subscriptions.push(disposable);

    disposable = vscode.commands.registerCommand('moat.sidecar.start', async () => {
        await startSidecar(api, moatPath);
    });

    context.subscriptions.push(disposable);

    disposable = vscode.commands.registerCommand('moat.sidecar.status', async () => {
        await showSidecarStatus(api);
    });

    context.subscriptions.push(disposable);

    // Auto-run on save if enabled
    if (config.get<boolean>('runOnSave', true)) {
        const onSaveDisposable = vscode.workspace.onDidSaveTextDocument(async (document) => {
            if (isSupportedLanguage(document.languageId)) {
                await runMoatCheck(api, moatPath, false); // Silent mode
            }
        });
        context.subscriptions.push(onSaveDisposable);
    }

    // Start Sidecar on activation if enabled
    if (config.get<boolean>('sidecar.enabled', true)) {
        startSidecar(api, moatPath).catch(console.error);
    }
}

function isSupportedLanguage(languageId: string): boolean {
    const supported = ['python', 'typescript', 'javascript'];
    return supported.includes(languageId);
}

async function runMoatCheck(api: AxiosInstance, moatPath: string, showOutput: boolean = true): Promise<void> {
    try {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }

        if (showOutput) {
            vscode.window.showInformationMessage('Running Moat check...');
        }

        // Try Sidecar API first
        try {
            const response = await api.post('/check', {
                projectPath: workspaceFolder.uri.fsPath,
            });

            const result = response.data;
            displayDiagnostics(result);

            if (result.errors && result.errors.length > 0) {
                vscode.window.showWarningMessage(
                    `Moat: ${result.errors.length} issue(s) found`
                );
            } else if (showOutput) {
                vscode.window.showInformationMessage('Moat: All checks passed!');
            }
        } catch (sidecarError) {
            // Fallback to direct CLI
            console.log('Sidecar not available, running CLI directly');
            await runMoatCLI(moatPath, workspaceFolder.uri.fsPath, ['check']);
        }
    } catch (error: any) {
        vscode.window.showErrorMessage(`Moat check failed: ${error.message}`);
    }
}

async function runMoatCLI(moatPath: string, projectPath: string, args: string[]): Promise<void> {
    const { exec } = require('child_process');
    const terminal = vscode.window.createTerminal('Moat');
    terminal.sendText(`${moatPath} ${args.join(' ')} --project "${projectPath}"`);
    terminal.show();
}

async function showMoatFix(api: AxiosInstance, moatPath: string): Promise<void> {
    try {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }

        vscode.window.showInformationMessage('Fetching AI fix suggestions...');

        // Try Sidecar API
        try {
            const response = await api.post('/fix', {
                projectPath: workspaceFolder.uri.fsPath,
            });

            const suggestions = response.data.suggestions || [];
            if (suggestions.length === 0) {
                vscode.window.showInformationMessage('No fixable issues found');
                return;
            }

            // Show quick pick
            const items = suggestions.map((s: any, index: number) => ({
                label: `${s.error.type}: ${s.error.message}`,
                description: `File: ${s.error.file}`,
                detail: s.strategy.suggestion,
                suggestion: s,
            }));

            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: `Select an issue to fix (${suggestions.length} found)`,
            });

            if (selected) {
                await showFixDetail(selected.suggestion);
            }
        } catch (sidecarError) {
            // Fallback to CLI
            await runMoatCLI(moatPath, workspaceFolder.uri.fsPath, ['fix']);
        }
    } catch (error: any) {
        vscode.window.showErrorMessage(`Moat fix failed: ${error.message}`);
    }
}

async function showFixDetail(suggestion: any): Promise<void> {
    const panel = vscode.window.createWebviewPanel(
        'moatFix',
        'Moat Fix Suggestion',
        vscode.ViewColumn.Beside,
        { enableScripts: true }
    );

    panel.webview.html = `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: var(--vscode-font-family); padding: 20px; }
                h1 { color: var(--vscode-textLink-foreground); }
                .field { margin: 15px 0; }
                label { font-weight: bold; color: var(--vscode-textLink-foreground); }
                pre { background: var(--vscode-textCodeBlock-background); padding: 10px; border-radius: 4px; }
                code { font-family: var(--vscode-editor-font-family); }
            </style>
        </head>
        <body>
            <h1>🔧 ${suggestion.strategy_type}</h1>
            <div class="field">
                <label>File:</label>
                <p><code>${suggestion.file}:${suggestion.line || '?'}</code></p>
            </div>
            <div class="field">
                <label>Issue:</label>
                <p>${suggestion.message}</p>
            </div>
            <div class="field">
                <label>Suggestion:</label>
                <p>${suggestion.suggestion}</p>
            </div>
            <div class="field">
                <label>Example:</label>
                <pre><code>${suggestion.example || 'No example available'}</code></pre>
            </div>
            <div class="field">
                <label>Confidence:</label>
                <p>${Math.round(suggestion.confidence * 100)}%</p>
            </div>
            <p style="color: var(--vscode-descriptionForeground);">
                ${suggestion.auto_fixable ? '✅ Supports auto-fix' : '⚠️ Manual fix required'}
            </p>
        </body>
        </html>
    `;
}

async function runMoatInit(moatPath: string): Promise<void> {
    await runMoatCLI(moatPath, vscode.workspace.workspaceFolders![0].uri.fsPath, ['init']);
}

async function startSidecar(api: AxiosInstance, moatPath: string): Promise<void> {
    try {
        await api.post('/sidecar/start');
        vscode.window.showInformationMessage('Moat Sidecar started');
    } catch (error) {
        // Fallback to CLI
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (workspaceFolder) {
            await runMoatCLI(moatPath, workspaceFolder.uri.fsPath, ['sidecar', 'start']);
        }
    }
}

async function showSidecarStatus(api: AxiosInstance): Promise<void> {
    try {
        const response = await api.get('/sidecar/status');
        const status = response.data;

        const message = status.running
            ? `Sidecar running (PID: ${status.pid})`
            : 'Sidecar stopped';

        vscode.window.showInformationMessage(`Moat Sidecar: ${message}`);
    } catch (error: any) {
        vscode.window.showWarningMessage('Sidecar not available');
    }
}

function displayDiagnostics(result: any): void {
    if (!result.errors || result.errors.length === 0) {
        vscode.languages.setTextDocumentDiagnostics([]);
        return;
    }

    const diagnostics: vscode.Diagnostic[] = [];

    for (const error of result.errors) {
        const uri = vscode.Uri.file(error.file);
        const document = vscode.workspace.textDocuments.find(
            (doc) => doc.uri.fsPath === error.file
        );

        if (document) {
            const range = new vscode.Range(
                new vscode.Position(error.line || 0, 0),
                new vscode.Position(error.line || 0, 1000)
            );

            const diagnostic = new vscode.Diagnostic(
                range,
                error.message,
                getSeverity(error.level)
            );

            diagnostic.source = 'Moat';
            diagnostics.push(diagnostic);
        }
    }

    const collection = vscode.languages.createDiagnosticCollection('moat');
    for (const doc of vscode.workspace.textDocuments) {
        const docDiagnostics = diagnostics.filter((d) => d.range);
        collection.set(doc.uri, docDiagnostics);
    }
}

function getSeverity(level: string): vscode.DiagnosticSeverity {
    switch (level?.toUpperCase()) {
        case 'ERROR':
        case 'CRITICAL':
            return vscode.DiagnosticSeverity.Error;
        case 'WARN':
        case 'WARNING':
        case 'HIGH':
            return vscode.DiagnosticSeverity.Warning;
        case 'MEDIUM':
            return vscode.DiagnosticSeverity.Information;
        default:
            return vscode.DiagnosticSeverity.Hint;
    }
}

export function deactivate() {
    console.log('Moat extension deactivated');
}
