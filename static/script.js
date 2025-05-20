document.addEventListener('DOMContentLoaded', function() {
    const socket = io({
        reconnectionAttempts: 5, 
        reconnectionDelay: 3000  
    });

    socket.on('connect', () => {
        console.log('已连接到 Socket.IO 服务器');
    });

    socket.on('connect_error', (err) => {
        console.error('Socket.IO 连接错误:', err);
        const playerInfoDiv = document.getElementById('player-info');
        if (playerInfoDiv) {
            playerInfoDiv.innerHTML = `<p style="color: var(--error-color);"><i class="fas fa-wifi-slash"></i> 无法连接到实时服务。</p>`;
        }
    });

    socket.on('disconnect', (reason) => {
        console.log('已从 Socket.IO 服务器断开:', reason);
    });

    initializeTabs();
    initializeTheme();
    StatusUpdates(socket);

    const downloadForm = document.getElementById('download-form');
    if (downloadForm) {
        downloadForm.addEventListener('submit', (event) => handleDownloadSubmit(event, socket));
    }

    const themeToggleButton = document.getElementById('theme-toggle-button');
    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', toggleTheme);
    }

    const playlistChoiceSelect = document.getElementById('playlist-choice-select');
    const playlistNameInput = document.getElementById('playlist-name');
    if (playlistChoiceSelect && playlistNameInput) {
        playlistChoiceSelect.addEventListener('change', function() {
            if (this.value === '__NEW__') {
                playlistNameInput.style.display = 'block';
                playlistNameInput.value = '';
                playlistNameInput.placeholder = '输入新播放列表名称';
                playlistNameInput.focus();
            } else {
                playlistNameInput.style.display = 'none';
                playlistNameInput.value = this.value;
            }
        });
        if (playlistChoiceSelect.value !== '__NEW__') {
            playlistNameInput.style.display = 'none';
            playlistNameInput.value = playlistChoiceSelect.value;
        } else {
            playlistNameInput.style.display = 'block';
        }
    }
});

function initializeTabs() {
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');
    if (tabLinks.length > 0 && tabContents.length > 0) {
        let activeFound = false;
        tabLinks.forEach(link => {
            if (link.dataset.tab === 'player-status') {
                link.classList.add('active');
                const content = document.getElementById('player-status-content');
                if(content) content.classList.add('active');
                activeFound = true;
            } else {
                link.classList.remove('active');
            }
        });
        tabContents.forEach(content => {
             if (content.id === 'player-status-content' && activeFound) {
                content.classList.add('active');
             } else {
                content.classList.remove('active');
             }
        });

        if (!activeFound && tabLinks.length > 0) {
            tabLinks[0].classList.add('active');
            tabContents[0].classList.add('active');
        }
    }
    tabLinks.forEach(link => {
        link.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            tabLinks.forEach(l => l.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            const contentToShow = document.getElementById(tabId + '-content');
            if (contentToShow) contentToShow.classList.add('active');
        });
    });
}

function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (savedTheme) document.body.classList.toggle('dark-theme', savedTheme === 'dark');
    else if (prefersDark) document.body.classList.add('dark-theme');
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
        if (!localStorage.getItem('theme')) document.body.classList.toggle('dark-theme', event.matches);
    });
}

function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark' : 'light');
}

function StatusUpdates(socket) {
    socket.on('update_status', (data) => {
        if (data.updated_type === 'player_status_updated') {
            UpdatesPlayer(data);
        } else if (data.updated_type === 'music_library_updated') {
            refreshMusicList(data);
        } else if (data.updated_type === 'download_status_updated') {
            updateDownloadStatusUI(data);
        }
    });
    socket.emit('update_status');
}

function UpdatesPlayer(data) {
    const playerInfoDiv = document.getElementById('player-info');
    if (!playerInfoDiv) return;
    playerInfoDiv.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> 连接到播放器状态服务...</p>';
    
    try {
        playerInfoDiv.innerHTML = data.error ? `<p style="color: var(--error-color);"><i class="fas fa-exclamation-circle"></i> 获取播放器状态失败: ${data.error}</p>` : (data.message || '<p>未能获取播放器状态。</p>');
    } catch (e) {
        playerInfoDiv.innerHTML = `<p style="color: var(--error-color);"><i class="fas fa-exclamation-triangle"></i> 解析播放器状态时出错。</p>`;
    }
}

function escapeJSString(str) {
    if (typeof str !== 'string') return '';
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}

function refreshMusicList(data) {
    const musicLibraryDiv = document.getElementById('music-library');
    if (!musicLibraryDiv) return;
    musicLibraryDiv.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> 正在加载音乐列表...</p>';

    if (data.error) {
        musicLibraryDiv.innerHTML = `<p style="color: var(--error-color);"><i class="fas fa-exclamation-circle"></i> 获取音乐列表失败: ${data.error}</p>`;
        populatePlaylistDropdown([]);
        return;
    }

    if (data.message && (!data.music_list || data.music_list.length === 0)) {
        musicLibraryDiv.innerHTML = `<p><i class="fas fa-info-circle"></i> ${data.message}</p>`;
        populatePlaylistDropdown([]);
        return;
    }

    if (data.music_list && data.music_list.length > 0) {
        let htmlContent = '';
        const playlistsForDropdown = [];

        data.music_list.forEach(item => {
            const itemName = escapeJSString(item.name);

            if (item.type === 'mp3') {
                const itemPath = escapeJSString(item.path);
                htmlContent += `
                    <div class="music-entry">
                        <span><i class="fas fa-music"></i> ${itemName}</span>
                        <div class="music-actions">
                            <button class="delete-button action-button small-action danger-action" onclick="handleDeleteSubmit('${itemPath}', '${itemName}')" title="删除此歌曲"><i class="fas fa-trash-alt"></i> 删除</button>
                        </div>
                    </div>`;
            } else if (item.type === 'playlist' && Array.isArray(item.path)) {
                playlistsForDropdown.push({ name: item.name }); 
                const playlistNameForJS = escapeJSString(item.name); 

                const playlistSongsHTML = item.path.length > 0
                    ? item.path.map(song => {
                        const songName = escapeJSString(song.name);
                        const songPath = escapeJSString(song.path);
                        return `
                            <div class="music-entry">
                                <span><i class="fas fa-file-audio"></i> ${songName}</span>
                                <div class="music-actions">
                                    <button class="delete-button action-button small-action danger-action" onclick="handleDeleteSubmit('${songPath}', '${songName}')" title="从此播放列表移除"><i class="fas fa-times-circle"></i> 移除</button>
                                </div>
                            </div>`;
                    }).join('')
                    : '<span><i class="fas fa-info-circle"></i> (空播放列表)</span>';

                htmlContent += `
                    <div class="playlist-entry">
                        <div class="playlist-title-container">
                            <strong><i class="fas fa-folder-open"></i> ${itemName} (播放列表)</strong>
                            <div class="playlist-actions">
                                <button class="delete-button action-button small-action danger-action" onclick="handleDeleteSubmit('${playlistNameForJS}')" title="删除此播放列表"><i class="fas fa-trash-alt"></i> 删除列表</button>
                            </div>
                        </div>
                        <div class="playlist-songs">
                            ${playlistSongsHTML}
                        </div>
                    </div>`;
            }
        });

        musicLibraryDiv.innerHTML = htmlContent;
        populatePlaylistDropdown(playlistsForDropdown);
    } else {
        musicLibraryDiv.innerHTML = '<p><i class="fas fa-box-open"></i> 音乐库为空。</p>';
        populatePlaylistDropdown([]);
    }
}

async function handleDeleteSubmit(itemPath, itemName) {
    const displayName = itemName || itemPath.split('/').pop();

    if (!confirm(`您确定要删除 "${displayName}" 吗？这个操作无法撤销。`)) {
        return;
    }

    const feedbackContainer = document.getElementById('music-library-feedback'); 
    if (!feedbackContainer) {
        console.error("Music library feedback container not found!");
        alert("发生内部错误，无法显示删除反馈。");
        return;
    }

    feedbackContainer.innerHTML = ''; 

    const feedbackItem = document.createElement('div');
    feedbackItem.classList.add('download-item'); 
    feedbackItem.innerHTML = `
        <p class="download-title"><i class="fas fa-spinner fa-spin"></i> 正在删除 ${escapeJSString(displayName)}...</p>
        <p class="status-message pending" id="delete-status-${Date.now()}">请稍候...</p>`;
    feedbackContainer.prepend(feedbackItem); 

    try {
        const fetchResponse = await fetch('/mp3/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ item_path: itemPath })
        });

        const response = await fetchResponse.json();
        const statusP = feedbackItem.querySelector('.status-message');
        const titleP = feedbackItem.querySelector('.download-title');

        if (response.status === 'success') {
            titleP.innerHTML = `<i class="fas fa-check-circle"></i> 删除成功`;
            statusP.textContent = response.message;
            statusP.className = 'status-message success';
            
            setTimeout(() => {
                feedbackItem.classList.add('fade-out-remove');
                feedbackItem.addEventListener('animationend', () => feedbackItem.remove());
            }, 3000);

        } else {
            titleP.innerHTML = `<i class="fas fa-exclamation-triangle"></i> 删除失败`;
            statusP.textContent = response.message;
            statusP.className = 'status-message error';
            setTimeout(() => {
                feedbackItem.classList.add('fade-out-remove');
                feedbackItem.addEventListener('animationend', () => feedbackItem.remove());
            }, 5000);
        }

    } catch (error) {
        console.error("删除请求失败:", error);
        const statusP = feedbackItem.querySelector('.status-message');
        const titleP = feedbackItem.querySelector('.download-title');
        titleP.innerHTML = `<i class="fas fa-exclamation-triangle"></i> 删除请求错误`;
        statusP.textContent = `请求无法发送或处理: ${error.message || error}`;
        statusP.className = 'status-message error';
        setTimeout(() => {
            feedbackItem.classList.add('fade-out-remove');
            feedbackItem.addEventListener('animationend', () => feedbackItem.remove());
        }, 5000);
    }
}

function populatePlaylistDropdown(playlists) {
    const playlistChoiceSelect = document.getElementById('playlist-choice-select');
    const playlistNameInput = document.getElementById('playlist-name');
    if (!playlistChoiceSelect || !playlistNameInput) return;

    const currentSelectedValue = playlistChoiceSelect.value;
    const currentTextInputValue = playlistNameInput.value;
    const isTextInputVisible = playlistNameInput.style.display === 'block';

    while (playlistChoiceSelect.options.length > 2) {
        playlistChoiceSelect.remove(2);
    }

    playlists.forEach(pl => {
        const option = document.createElement('option');
        option.value = pl.name;
        option.textContent = pl.name;
        playlistChoiceSelect.appendChild(option);
    });

    if (currentSelectedValue) {
        let valueStillExists = Array.from(playlistChoiceSelect.options).some(opt => opt.value === currentSelectedValue);
        if (valueStillExists) {
            playlistChoiceSelect.value = currentSelectedValue;
        } else if (currentSelectedValue === '__NEW__') {
             playlistChoiceSelect.value = '__NEW__';
        } else {
            playlistChoiceSelect.value = "";
        }
    } else {
         playlistChoiceSelect.value = "";
    }

    if (playlistChoiceSelect.value === '__NEW__') {
        playlistNameInput.style.display = 'block';
        if (isTextInputVisible) {
            playlistNameInput.value = currentTextInputValue;
        } else {
            playlistNameInput.value = '';
        }
    } else {
        playlistNameInput.style.display = 'none';
        playlistNameInput.value = playlistChoiceSelect.value;
    }
}

async function handleDownloadSubmit(event, socket) {
    event.preventDefault();

    const urlInput = document.getElementById('video-url');
    const playlistChoiceSelect = document.getElementById('playlist-choice-select');
    const playlistNameInput = document.getElementById('playlist-name');
    const downloadFeedbackContainer = document.getElementById('download-feedback-container');

    if (!urlInput || !playlistChoiceSelect || !playlistNameInput || !downloadFeedbackContainer) return;

    const url = urlInput.value.trim();
    let targetPlaylistName = '';

    if (!url) {
        alert('请输入视频链接。');
        urlInput.focus();
        return;
    }

    if (playlistChoiceSelect.value === '__NEW__') {
        targetPlaylistName = playlistNameInput.value.trim();
        if (!targetPlaylistName) {
            alert('如果您选择创建新播放列表，请输入播放列表名称。');
            playlistNameInput.focus();
            return;
        }
    } else {
        targetPlaylistName = playlistChoiceSelect.value;
    }

    downloadFeedbackContainer.innerHTML = '';

    try {
        const fetchResponse = await fetch('/mp3/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                playlist: targetPlaylistName,
                sid: socket.id
            })
        });
        const response = await fetchResponse.json();

        if (response.status === 'error') {
            const errorDiv = document.createElement('div');
            errorDiv.classList.add('download-item');
            errorDiv.innerHTML = `
                <p class="download-title"><i class="fas fa-exclamation-triangle"></i> 下载提交错误</p>
                <p class="status-message error">${response.message}</p>`;
            downloadFeedbackContainer.prepend(errorDiv);
        } else if (response.status === 'pending') {
            const feedbackItem = document.createElement('div');
            feedbackItem.classList.add('download-item');
            feedbackItem.innerHTML = `
                <p class="download-title">下载: ${url.length > 50 ? url.substring(0, 47) + '...' : url}${targetPlaylistName ? ` (到播放列表: ${targetPlaylistName})` : ''}</p>
                <p class="status-message pending" id="status"><i class="fas fa-spinner fa-spin"></i> 状态: 初始化中...</p>
                <div class="progress-bar-container" id="pbc" style="display: none;">
                    <div class="progress-bar" id="pb" style="width: 0%;">0%</div>
                </div>`;
            downloadFeedbackContainer.prepend(feedbackItem);

            urlInput.value = '';
            playlistChoiceSelect.value = '';
            playlistNameInput.style.display = 'none';
            playlistNameInput.value = '';
        }
    } catch (error) {
        console.error(`请求失败: ${error}`);
        const errorDiv = document.createElement('div');
        errorDiv.classList.add('download-item');
        errorDiv.innerHTML = `
            <p class="download-title"><i class="fas fa-exclamation-triangle"></i> 下载提交错误</p>
            <p class="status-message error">${error}</p>`;
        downloadFeedbackContainer.prepend(errorDiv);
    }
}

function updateDownloadStatusUI(data) {
    if (!data) {
        return;
    }
    const statusElement = document.getElementById(`status`);
    const progressBarContainer = document.getElementById(`pbc`);
    const progressBar = document.getElementById(`pb`);

    if (!statusElement || !progressBarContainer || !progressBar) {
        return;
    }
    
    statusElement.className = 'status-message';
    let titleText = data.title ? ` - ${escapeJSString(data.title)}` : '';

    if (data.status === "error") {
        statusElement.innerHTML = `<i class="fas fa-exclamation-circle"></i> 错误: ${data.extra}`;
        statusElement.classList.add('error');
        progressBarContainer.style.display = 'none';
    } else if (data.status === "downloading") {
        if (data.extra !== 100.0) {
            statusElement.innerHTML = `<i class="fas fa-download"></i> 状态: 下载中${titleText}`;
            statusElement.classList.add('pending');
            const percentage = parseFloat(data.extra) || 0;
            progressBarContainer.style.display = 'block';
            progressBar.style.width = `${percentage}%`; progressBar.textContent = `${percentage.toFixed(0)}%`;
            progressBar.classList.remove('error'); progressBar.style.backgroundColor = 'var(--accent-color)';
        } else {
            statusElement.innerHTML = `<i class="fas fa-check-circle"></i> 完成: ${data.title || '下载成功!'}`;
            statusElement.classList.add('success');
            progressBarContainer.style.display = 'block'; progressBar.style.width = '100%'; progressBar.textContent = '100%';
            progressBar.classList.remove('error'); progressBar.style.backgroundColor = 'var(--accent-color)';
        }
    } 
}