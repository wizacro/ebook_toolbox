import { useState, useEffect } from 'react';

const API_BASE = 'http://127.0.0.1:8000';

interface SettingsState {
  zlibrary_email: string;
  zlibrary_password: string;
  zlibrary_remix_userid: string;
  zlibrary_remix_userkey: string;
  zlibrary_domain: string;
  local_library_dir: string;
  local_output_dir: string;
  booklist_save_dir: string;
  booklist_use_local_index: string;
}

const EMPTY_SETTINGS: SettingsState = {
  zlibrary_email: '',
  zlibrary_password: '',
  zlibrary_remix_userid: '',
  zlibrary_remix_userkey: '',
  zlibrary_domain: '',
  local_library_dir: '',
  local_output_dir: '',
  booklist_save_dir: '',
  booklist_use_local_index: 'false',
};

const hintStyle: React.CSSProperties = {
  display: 'block',
  marginTop: '0.35rem',
  fontSize: '0.78rem',
  color: '#8b9bb4',
  lineHeight: 1.5,
};

export default function SettingsPanel() {
  const [settings, setSettings] = useState<SettingsState>(EMPTY_SETTINGS);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    fetch(`${API_BASE}/api/settings`)
      .then(res => res.json())
      .then(data => {
        setSettings({
          zlibrary_email: data.email || '',
          zlibrary_password: data.password || '',
          zlibrary_remix_userid: data.remix_userid || '',
          zlibrary_remix_userkey: data.remix_userkey || '',
          zlibrary_domain: data.domain || '',
          local_library_dir: data.local_library_dir || '',
          local_output_dir: data.local_output_dir || '',
          booklist_save_dir: data.booklist_save_dir || '',
          booklist_use_local_index: (data.booklist_use_local_index || 'false') === 'true' ? 'true' : 'false',
        });
      });
  }, []);

  const set = (key: keyof SettingsState, value: string) =>
    setSettings(s => ({ ...s, [key]: value }));

  const handleSave = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/api/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
      });
      setMsg('设置已保存');
      setTimeout(() => setMsg(''), 3000);
    } catch (e) {
      setMsg('保存失败！');
    }
    setLoading(false);
  };

  return (
    <section className="glass-panel">
      <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem', color: '#f8fafc' }}>Z-Library 账户设置</h2>
      <div className="settings-form">
        <div className="form-group">
          <label>邮箱 (email)</label>
          <input 
            value={settings.zlibrary_email} 
            onChange={e => set('zlibrary_email', e.target.value)} 
            placeholder="your_email@example.com" 
          />
        </div>
        <div className="form-group">
          <label>密码 (password)</label>
          <input 
            type="password"
            value={settings.zlibrary_password} 
            onChange={e => set('zlibrary_password', e.target.value)} 
            placeholder="••••••••" 
          />
        </div>
        <div className="form-group">
          <label>Remix User ID (备用)</label>
          <input 
            value={settings.zlibrary_remix_userid} 
            onChange={e => set('zlibrary_remix_userid', e.target.value)} 
            placeholder="非必填" 
          />
        </div>
        <div className="form-group">
          <label>Remix User Key (备用)</label>
          <input 
            value={settings.zlibrary_remix_userkey} 
            onChange={e => set('zlibrary_remix_userkey', e.target.value)} 
            placeholder="非必填" 
          />
        </div>
      </div>

      <h2 style={{ margin: '2rem 0 0.5rem', fontSize: '1.5rem', color: '#f8fafc' }}>域名与路径配置</h2>
      <p style={{ color: '#8b9bb4', fontSize: '0.85rem', marginBottom: '1.25rem', lineHeight: 1.6 }}>
        保存后立即生效：书单下载、“书单批量下载”等任务都会使用以下域名与默认路径。
      </p>
      <div className="settings-form">
        <div className="form-group">
          <label>Z-Library 镜像域名</label>
          <input 
            value={settings.zlibrary_domain} 
            onChange={e => set('zlibrary_domain', e.target.value)} 
            placeholder="zh.zlib.bz" 
          />
          <span style={hintStyle}>书单页网址所使用的域名（如 zh.zlib.bz）。若某天下载失败，先在浏览器确认哪个 Z-Lib 域名能打开书单页，再改成它。</span>
        </div>
        <div className="form-group">
          <label>书单下载保存目录</label>
          <input 
            value={settings.booklist_save_dir} 
            onChange={e => set('booklist_save_dir', e.target.value)} 
            placeholder="E:\zlibrary_booklists" 
          />
          <span style={hintStyle}>“Z-Library 书单下载（按网址）”的保存位置，每个书单自动建一个子文件夹。</span>
        </div>
        <div className="form-group">
          <label>本地书库目录</label>
          <input 
            value={settings.local_library_dir} 
            onChange={e => set('local_library_dir', e.target.value)} 
            placeholder={'E:\\'}
          />
          <span style={hintStyle}>本地电子书的存放根目录；本地搜索整理与书单下载查重的起点。整个盘（如 E:\）或某个书库文件夹均可。</span>
        </div>
        <div className="form-group">
          <label>默认整理输出目录</label>
          <input 
            value={settings.local_output_dir} 
            onChange={e => set('local_output_dir', e.target.value)} 
            placeholder="E:\书单" 
          />
          <span style={hintStyle}>“本地电子书搜索与整理”等卡片中输出目录的默认值（运行时仍可在卡片里临时修改）。</span>
        </div>
        <div className="param-checkbox-group" style={{ marginBottom: '0.5rem' }}>
          <input
            type="checkbox"
            id="booklist_use_local_index"
            checked={settings.booklist_use_local_index === 'true'}
            onChange={e => set('booklist_use_local_index', e.target.checked ? 'true' : 'false')}
          />
          <label className="checkbox-label" htmlFor="booklist_use_local_index">
            书单下载时先在本地书库查重（首次需建全盘索引，较慢；已有本地书库时再开启）
          </label>
        </div>
      </div>
      <div style={{ marginTop: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <button onClick={handleSave} disabled={loading}>
          {loading ? '正在保存...' : '保存设置'}
        </button>
        {msg && <span style={{ color: msg.includes('失败') ? 'var(--danger-color)' : 'var(--success-color)', fontSize: '0.9rem' }}>{msg}</span>}
      </div>
    </section>
  );
}
