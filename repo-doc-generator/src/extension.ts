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
	let showModuleDoc = vscode.commands.registerCommand('repoDoc.showModuleDoc', async (folder: vscode.Uri) => {
		try {
			// Находим имя и путь самой папки
			const folderPath = folder.fsPath;
			const folderName = path.basename(folderPath);

			// Формируем путь к файлу документации - в той же папке
			const docFilePath = vscode.Uri.file(path.join(folderPath, `${folderName}_module.md`));

			try {
				// Проверяем существование файла
				await fs.promises.access(docFilePath.fsPath);

				// Открываем файл в редакторе
				const doc = await vscode.workspace.openTextDocument(docFilePath);
				await vscode.window.showTextDocument(doc);
			} catch (error) {
				vscode.window.showErrorMessage(`Документация для модуля ${folderName} не найдена (${folderName}.md)`);
			}
		} catch (error) {
			vscode.window.showErrorMessage('Ошибка при открытии документации модуля');
		}
	});

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

		const zip = new JSZip();
		await addFolderToZip(zip, root, '');
		const zipBuffer = await zip.generateAsync({ type: "arraybuffer" });

		try {
			this._view.webview.postMessage({ status: 'Отправка на сервер...' });
			const resp = await axios.post(
				'http://localhost:8000/components/upload_and_extract/',
				zipBuffer,
				{
					headers: { 'Content-Type': 'application/zip' },
					responseType: 'arraybuffer'  // Изменено на arraybuffer для получения ZIP
				}
			);

			console.log('Получен ответ от сервера:', {
				status: resp.status,
				headers: resp.headers,
				dataLength: resp.data.byteLength
			});

			// Распаковываем полученный ZIP
			const receivedZip = await JSZip.loadAsync(resp.data);

			// Создаём/получаем output channel
			const outputChannel = vscode.window.createOutputChannel('Repo Doc Generator');

			// Выводим список всех файлов в ZIP
			outputChannel.appendLine('Содержимое полученного ZIP архива:');
			receivedZip.forEach((relativePath, entry) => {
				outputChannel.appendLine(`- ${relativePath} (${entry.name})`);
			});

			// Показываем панель
			// outputChannel.show();

			// Пробуем найти файл разными способами
			let directPath = '';
			Object.keys(receivedZip.files).forEach(filePath => {
				if (filePath.endsWith('project_overview.md')) {
					directPath = filePath;
				}
			});
			if (!directPath) {
				this._view.webview.postMessage({
					status: 'Ошибка',
					data: '<p style="color: red;">Файл project_overview.md не найден в ZIP архиве</p>'
				});
				return;
			}
			const overviewFile = receivedZip.file(directPath);

			console.log('Поиск файла:', {
				directPathExists: !!overviewFile,
				totalFiles: Object.keys(receivedZip.files).length,
				filesWithMd: Object.keys(receivedZip.files).filter(f => f.endsWith('.md'))
			});

			if (overviewFile) {
				const content = await overviewFile.async('string');
				console.log('Содержимое файла (первые 100 символов):', content.substring(0, 100));
				// Конвертируем Markdown в HTML (простая замена)
				const htmlContent = content
					.replace(/\n/g, '<br>')
					.replace(/#{3,}\s(.+)/g, '<h3>$1</h3>')
					.replace(/#{2}\s(.+)/g, '<h2>$1</h2>')
					.replace(/#\s(.+)/g, '<h1>$1</h1>');

				this._view.webview.postMessage({
					status: 'Анализ завершён',
					data: `<div class="markdown-body">${htmlContent}</div>`
				});
			} else {
				this._view.webview.postMessage({
					status: 'Ошибка',
					data: '<p style="color: red;">Файл project_overview.md не найден в ответе сервера</p>'
				});
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

