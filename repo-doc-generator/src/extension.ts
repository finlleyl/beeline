import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import JSZip from 'jszip';
import axios from 'axios';

export function activate(context: vscode.ExtensionContext) {
	const provider = new RepoDocSidebarProvider(context);
	// Регистрируем провайдер для WebviewView с id 'repoDocView'
	const disposable = (vscode.window as any).registerWebviewViewProvider('repoDocView', provider);
	context.subscriptions.push(disposable);

	// Регистрируем команду для показа документации модуля
	let showModuleDoc = vscode.commands.registerCommand(
		'repoDoc.showModuleDoc',
		async (folder: vscode.Uri) => {
			try {
				if (!folder) {
					vscode.window.showErrorMessage('Не выбрана папка');
					return;
				}

				const workspaceFolders = vscode.workspace.workspaceFolders;
				if (!workspaceFolders?.length) {
					vscode.window.showErrorMessage('Нет открытого рабочего пространства');
					return;
				}

				const workspaceRoot = workspaceFolders[0].uri.fsPath;
				const folderPath = folder.fsPath;
				const folderName = path.basename(folderPath);
				const relPath = path.relative(workspaceRoot, folderPath);

				const docFilePath = vscode.Uri.file(
					path.join(workspaceRoot, '.vscode-temp', 'content', 'generated_docs', relPath, `${folderName}_module.md`)
				);

				try {
					await fs.promises.stat(docFilePath.fsPath);
					const mdContent = await fs.promises.readFile(docFilePath.fsPath, 'utf-8');

					const panel = vscode.window.createWebviewPanel(
						'moduleDocumentation',
						`Документация: ${folderName}`,
						vscode.ViewColumn.Beside,
						{
							enableScripts: true,
							localResourceRoots: [vscode.Uri.file(path.dirname(docFilePath.fsPath))]
						}
					);

					panel.webview.html = `<!DOCTYPE html>
					<html>
					<head>
						<meta charset="UTF-8"/>
						<style>
							body {
								font-family: system-ui, -apple-system, sans-serif;
								line-height: 1.6;
								padding: 20px;
								max-width: 900px;
								margin: auto;
								color: var(--vscode-editor-foreground);
								background: var(--vscode-editor-background);
							}
							h1, h2, h3 { margin-top: 1.5em; }
							pre {
								background: var(--vscode-textBlockQuote-background);
								padding: 16px;
								border-radius: 6px;
								overflow: auto;
							}
							code {
								font-family: var(--vscode-editor-font-family);
								font-size: 85%;
							}
							blockquote {
								border-left: 4px solid var(--vscode-textBlockQuote-border);
								margin: 0;
								padding-left: 1em;
								opacity: 0.8;
							}
						</style>
					</head>
					<body>
						${parseMarkdown(mdContent)}
					</body>
					</html>`;

				} catch (err) {
					console.error('Error accessing file:', err);
					vscode.window.showErrorMessage(`Документация не найдена: ${docFilePath.fsPath}`);
				}
			} catch (error) {
				console.error('Command error:', error);
				vscode.window.showErrorMessage('Ошибка при открытии документации модуля');
			}
		}
	);

	function parseMarkdown(markdown: string): string {
		return markdown
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			// Headers
			.replace(/^### (.*$)/gm, '<h3>$1</h3>')
			.replace(/^## (.*$)/gm, '<h2>$1</h2>')
			.replace(/^# (.*$)/gm, '<h1>$1</h1>')
			// Code blocks
			.replace(/```(\w*)\n([\s\S]*?)```/gm, (_, lang, code) =>
				`<pre><code class="language-${lang}">${code.trim()}</code></pre>`)
			// Inline code
			.replace(/`([^`]+)`/g, '<code>$1</code>')
			// Bold and italic
			.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
			.replace(/\*([^*]+)\*/g, '<em>$1</em>')
			// Lists
			.replace(/^- (.*$)/gm, '<li>$1</li>')
			.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
			// Links and images
			.replace(/!\[(.*?)\]\((.*?)\)/g, '<img alt="$1" src="$2">')
			.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2">$1</a>')
			// Blockquotes
			.replace(/^> (.*$)/gm, '<blockquote>$1</blockquote>')
			// Paragraphs
			.replace(/\n\n/g, '</p><p>')
			.replace(/^(.+)$/gm, '$1<br>');
	}

	// Создаем декоратор с улучшенными стилями
	const decorationType = vscode.window.createTextEditorDecorationType({
		isWholeLine: true,
		before: {
			contentText: '',
			backgroundColor: new vscode.ThemeColor('editor.background'),
			color: new vscode.ThemeColor('editor.foreground'),
			fontStyle: 'normal',
			margin: '1em 0',
			width: '100%',
			height: 'auto'
		}
	});

	// Функция для обновления документации
	async function updateDocumentation(editor: vscode.TextEditor) {
		try {
			// 1. Путь к открытому файлу и корню рабочего пространства
			const filePath = editor.document.uri.fsPath;
			const workspaceFolders = vscode.workspace.workspaceFolders;
			if (!workspaceFolders || workspaceFolders.length === 0) {
				vscode.window.showErrorMessage('Нет открытого рабочего пространства');
				return;
			}
			const workspaceRoot = workspaceFolders[0].uri.fsPath;

			// 2. Директория и базовое имя файла
			const fileDir = path.dirname(filePath);
			const fileName = path.basename(filePath);
			const baseName = fileName.substring(0, fileName.lastIndexOf('.'));

			// 3. Относительный путь от корня до папки с файлом
			const relDir = path.relative(workspaceRoot, fileDir);

			// 4. Формируем путь в .vscode-temp/content/generated_docs
			const docDir = path.join(
				workspaceRoot,
				'.vscode-temp',
				'content',
				'generated_docs',
				relDir
			);
			const docPath = path.join(docDir, `${baseName}.md`);

			// 5. Проверяем существование и читаем содержимое
			if (fs.existsSync(docPath)) {
				const docContent = await fs.promises.readFile(docPath, 'utf-8');

				const decoration: vscode.DecorationOptions = {
					range: new vscode.Range(0, 0, 0, 0),
					renderOptions: {
						before: {
							contentText: docContent,
							backgroundColor: new vscode.ThemeColor('editor.background'),
							color: new vscode.ThemeColor('editor.foreground'),
							fontStyle: 'normal',
							margin: '1em 0'
						}
					}
				};

				editor.setDecorations(decorationType, [decoration]);
			} else {
				editor.setDecorations(decorationType, []);
			}
		} catch (error) {
			console.error('Error updating documentation:', error);
			vscode.window.showErrorMessage('Ошибка при обновлении документации');
		}
	}

	// Слушаем открытие и изменение активного редактора
	context.subscriptions.push(
		vscode.window.onDidChangeActiveTextEditor(editor => {
			if (editor) {
				console.log('Editor changed:', editor.document.uri.fsPath);
				updateDocumentation(editor);
			}
		})
	);

	// Обновляем документацию для уже открытого редактора
	if (vscode.window.activeTextEditor) {
		updateDocumentation(vscode.window.activeTextEditor);
	}

	context.subscriptions.push(showModuleDoc);
}

class RepoDocSidebarProvider {
	private _view?: any;

	constructor(private readonly _context: vscode.ExtensionContext) { }

	// Вызывается, когда открывается ваша вкладка в Activity Bar
	public resolveWebviewView(webviewView: any, _ctx: any, _token: vscode.CancellationToken) {
		this._view = webviewView;
		webviewView.webview.options = { enableScripts: true };
		webviewView.webview.html = this.getHtml();

		// Слушаем сообщения из Webview (только 'analyze')
		webviewView.webview.onDidReceiveMessage(async (msg: any) => {
			if (msg.command === 'analyze') {
				await this.analyzeRepo();
			}
		});
	}

	// Генерируем HTML с кнопкой и скриптом
	private getHtml(): string {
		return `<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8"/>
    <style>
        body, html { margin: 0; padding: 10px; height: 100%; }
        .form-container {
            display: flex;
            align-items: center;
            flex-direction: column;
            padding: 20px 0;
        }
        .btn-primary {
            background: linear-gradient(135deg, #6b73ff 0%, #000dff 100%);
            border: none; color: #fff;
            padding: 0.8em 2em; font-size: 1rem; font-weight: 600;
            border-radius: 2.5em;
            box-shadow: 0 4px 14px rgba(0,0,0,0.2);
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        .btn-primary:active {
            transform: translateY(0);
            box-shadow: 0 4px 14px rgba(0,0,0,0.2);
        }
        #status {
            margin-top: 1em;
            font-style: italic;
        }
        #result {
            margin-top: 20px;
            max-width: 100%;
            overflow-y: auto;
            padding: 10px;
        }
    </style>
</head>
<body>
    <div class="form-container">
        <button id="analyzeBtn" class="btn-primary">Анализ</button>
        <div id="status"></div>
        <div id="result"></div>
    </div>
    <script>
        const vscode = acquireVsCodeApi();
        const btn = document.getElementById('analyzeBtn');
        const status = document.getElementById('status');
        const result = document.getElementById('result');
        
        btn.addEventListener('click', () => {
            status.textContent = 'Запрос отправлен...';
            result.innerHTML = '';
            vscode.postMessage({ command: 'analyze' });
        });
        
        window.addEventListener('message', event => {
            if (event.data.status) {
                status.textContent = event.data.status;
            }
            if (event.data.data) {
                result.innerHTML = event.data.data;
            }
        });
    </script>
</body>
</html>`;
	}

	// Основная логика: архивируем, отправляем и открываем Webview с результатом
	private async analyzeRepo() {
		if (!this._view) {
			return;
		}
		this._view.webview.postMessage({ status: 'Начало анализа...' });

		const folders = vscode.workspace.workspaceFolders;
		if (!folders || folders.length === 0) {
			vscode.window.showErrorMessage('Откройте репозиторий перед анализом.');
			return;
		}
		const root = folders[0].uri.fsPath;

		// Создаем временную папку рядом с проектом
		const tempDir = path.join(root, '.vscode-temp');

		try {
			// Проверяем существование временной папки
			if (fs.existsSync(tempDir)) {
				this._view.webview.postMessage({ status: 'Используем существующую документацию...' });
				const extractedMdPath = path.join(tempDir, 'content/generated_docs/auctioning_platform/project_overview.md');

				if (fs.existsSync(extractedMdPath)) {
					const mdContent = await fs.promises.readFile(extractedMdPath, 'utf-8');
					// Конвертируем Markdown в HTML
					const htmlContent = mdContent
						.replace(/\n/g, '<br>')
						.replace(/#{3,}\s(.+)/g, '<h3>$1</h3>')
						.replace(/#{2}\s(.+)/g, '<h2>$1</h2>')
						.replace(/#\s(.+)/g, '<h1>$1</h1>');

					this._view.webview.postMessage({
						status: 'Анализ завершён',
						data: `<div class="markdown-body">${htmlContent}</div>`
					});
					return;
				}
			}

			// Если папки нет или файла в ней нет - создаём папку и делаем запрос
			if (!fs.existsSync(tempDir)) {
				await fs.promises.mkdir(tempDir, { recursive: true });
			}

			// Архивируем и отправляем на сервер
			const zip = new JSZip();
			await addFolderToZip(zip, root, '');
			const zipBuffer = await zip.generateAsync({ type: "arraybuffer" });

			this._view.webview.postMessage({ status: 'Отправка на сервер...' });
			const resp = await axios.post(
				'http://localhost:8000/components/upload_and_extract/',
				zipBuffer,
				{
					headers: { 'Content-Type': 'application/zip' },
					responseType: 'arraybuffer'
				}
			);

			// Распаковываем полученный ZIP в папку
			const receivedZip = await JSZip.loadAsync(resp.data);
			this._view.webview.postMessage({ status: 'Распаковка архива...' });

			// Извлекаем все файлы
			for (const [filename, file] of Object.entries(receivedZip.files)) {
				if (file.dir) {
					await fs.promises.mkdir(path.join(tempDir, filename), { recursive: true });
				} else {
					const content = await file.async('nodebuffer');
					const filePath = path.join(tempDir, filename);
					await fs.promises.mkdir(path.dirname(filePath), { recursive: true });
					await fs.promises.writeFile(filePath, content);
				}
			}

			// После распаковки читаем файл и отображаем
			const extractedMdPath = path.join(tempDir, 'content/generated_docs/auctioning_platform/project_overview.md');
			if (fs.existsSync(extractedMdPath)) {
				const mdContent = await fs.promises.readFile(extractedMdPath, 'utf-8');
				const htmlContent = mdContent
					.replace(/\n/g, '<br>')
					.replace(/#{3,}\s(.+)/g, '<h3>$1</h3>')
					.replace(/#{2}\s(.+)/g, '<h2>$1</h2>')
					.replace(/#\s(.+)/g, '<h1>$1</h1>');

				this._view.webview.postMessage({
					status: 'Анализ завершён',
					data: `<div class="markdown-body">${htmlContent}</div>`
				});
			} else {
				throw new Error('Файл не найден после распаковки');
			}

		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Неизвестная ошибка';
			this._view.webview.postMessage({
				status: 'Ошибка: ' + errorMessage,
				data: '<p style="color: red;">Произошла ошибка при обработке ответа</p>'
			});
		}
	}
}

// Рекурсивная функция архивации папок
async function addFolderToZip(zip: JSZip, folderPath: string, zipPath: string) {
	const entries = await fs.promises.readdir(folderPath, { withFileTypes: true });
	for (const entry of entries) {
		const full = path.join(folderPath, entry.name);
		const rel = path.posix.join(zipPath, entry.name);
		if (entry.isDirectory()) {
			if (entry.name === 'node_modules' || entry.name === '.git') continue;
			await addFolderToZip(zip, full, rel);
		} else {
			const data = await fs.promises.readFile(full);
			zip.file(rel, data);
		}
	}
}

export function deactivate() { }

function fetch(uri: any) {
	throw new Error('Function not implemented.');
}

