"""
web_app.py
Web 界面 + 实时预览

Flask 应用，提供：
- 视频上传
- 参数配置
- 实时预览剪辑点
- 处理进度显示
- 下载结果
"""

import os
import json
import uuid
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file

# 导入核心模块
from dance_clipper import DanceClipper, ClipConfig
from dance_presets import PresetManager, list_dance_types, get_preset
from gpu_accelerator import GPUAccelerator

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB 上传限制

# 上传目录
UPLOAD_FOLDER = Path(tempfile.gettempdir()) / 'dance_clipper_uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

# 任务状态存储
# 实际生产环境应该用 Redis 或数据库
tasks = {}


class ClipTask:
    """剪辑任务"""
    def __init__(self, task_id: str, filename: str):
        self.task_id = task_id
        self.filename = filename
        self.status = 'pending'  # pending, processing, completed, failed
        self.progress = 0
        self.message = '等待处理'
        self.result_path = None
        self.report = None
        self.created_at = datetime.now()
        self.completed_at = None
        
    def to_dict(self):
        return {
            'task_id': self.task_id,
            'filename': self.filename,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'result_path': self.result_path,
            'report': self.report,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


# ==================== 路由 ====================

@app.route('/')
def index():
    """主页面"""
    presets = list_dance_types()
    gpu = GPUAccelerator()
    
    return render_template('index.html', 
                          presets=presets,
                          gpu_available=gpu.is_available())


@app.route('/api/upload', methods=['POST'])
def upload_video():
    """上传视频"""
    if 'video' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    # 生成任务ID
    task_id = str(uuid.uuid4())[:8]
    
    # 保存文件
    ext = Path(file.filename).suffix
    saved_name = f"{task_id}{ext}"
    file_path = UPLOAD_FOLDER / saved_name
    file.save(file_path)
    
    # 创建任务
    task = ClipTask(task_id, file.filename)
    task.input_path = str(file_path)
    tasks[task_id] = task
    
    return jsonify({
        'task_id': task_id,
        'filename': file.filename,
        'message': '上传成功'
    })


@app.route('/api/preview', methods=['POST'])
def preview_clip():
    """预览剪辑点（不实际剪辑）"""
    data = request.json
    task_id = data.get('task_id')
    
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    
    # 获取参数
    preset_name = data.get('preset', 'ballet')
    target_duration = float(data.get('target_duration', 30))
    
    try:
        # 获取预设
        preset = get_preset(preset_name)
        
        # 创建配置
        config = ClipConfig(
            target_duration=target_duration,
            tolerance=2.0,
            min_segment_duration=preset.min_segment_duration,
            audio_weight=preset.audio_weight,
            video_weight=preset.video_weight,
            bpm_range=preset.bpm_range
        )
        
        # 预览模式：只分析，不剪辑
        clipper = DanceClipper(config)
        
        # 这里简化处理，实际应该返回分析结果
        # 提取音频分析
        audio_path = clipper._extract_audio(task.input_path)
        beats = clipper._analyze_audio(audio_path)
        video_info = clipper._analyze_video(task.input_path)
        candidates = clipper._generate_candidates(beats, video_info)
        
        # 选择最优片段
        selected = clipper._select_optimal_segments(candidates)
        
        # 清理临时文件
        clipper._cleanup()
        
        # 生成预览数据
        preview_data = {
            'duration': video_info['duration'],
            'bpm': beats[0].bpm if beats else 120,
            'detected_dance_type': PresetManager.auto_detect_preset(
                beats[0].bpm if beats else 120
            ),
            'segments': [
                {
                    'start': s.start,
                    'end': s.end,
                    'duration': s.end - s.start,
                    'music_score': s.music_score,
                    'motion_score': s.motion_score,
                    'total_score': s.total_score
                }
                for s in selected[:3]  # 返回前3个候选
            ],
            'timeline': [
                {'time': b.time, 'is_downbeat': b.is_downbeat}
                for b in beats[:50]  # 前50个节拍
            ]
        }
        
        return jsonify({
            'success': True,
            'preview': preview_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clip', methods=['POST'])
def start_clip():
    """开始剪辑"""
    data = request.json
    task_id = data.get('task_id')
    
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    
    # 获取参数
    preset_name = data.get('preset', 'ballet')
    target_duration = float(data.get('target_duration', 30))
    use_gpu = data.get('use_gpu', True)
    
    # 后台处理
    def process():
        try:
            task.status = 'processing'
            task.message = '正在分析...'
            task.progress = 10
            
            # 获取预设
            preset = get_preset(preset_name)
            
            # 创建配置
            config = ClipConfig(
                target_duration=target_duration,
                tolerance=2.0,
                min_segment_duration=preset.min_segment_duration,
                audio_weight=preset.audio_weight,
                video_weight=preset.video_weight,
                bpm_range=preset.bpm_range
            )
            
            task.progress = 30
            task.message = '正在剪辑...'
            
            # 输出路径
            output_path = UPLOAD_FOLDER / f"{task_id}_output.mp4"
            
            # 检查 GPU
            gpu = GPUAccelerator()
            if use_gpu and gpu.is_available():
                task.message = '使用 GPU 加速剪辑...'
            
            # 执行剪辑
            clipper = DanceClipper(config)
            report = clipper.clip(task.input_path, str(output_path))
            
            task.progress = 100
            task.status = 'completed'
            task.message = '剪辑完成'
            task.result_path = str(output_path)
            task.report = report
            task.completed_at = datetime.now()
            
        except Exception as e:
            task.status = 'failed'
            task.message = f'剪辑失败: {str(e)}'
    
    # 启动后台线程
    thread = threading.Thread(target=process)
    thread.start()
    
    return jsonify({
        'success': True,
        'message': '剪辑任务已启动',
        'task_id': task_id
    })


@app.route('/api/status/<task_id>')
def get_status(task_id):
    """获取任务状态"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify(tasks[task_id].to_dict())


@app.route('/api/download/<task_id>')
def download_result(task_id):
    """下载剪辑结果"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    
    if task.status != 'completed' or not task.result_path:
        return jsonify({'error': '剪辑尚未完成'}), 400
    
    return send_file(
        task.result_path,
        as_attachment=True,
        download_name=f"dance_clip_{task_id}.mp4"
    )


@app.route('/api/presets')
def get_presets():
    """获取所有预设"""
    presets = {}
    for name in PresetManager.get_preset_names():
        preset = get_preset(name)
        presets[name] = {
            'name_cn': preset.name_cn,
            'description': preset.description,
            'bpm_range': preset.bpm_range,
            'bpm_typical': preset.bpm_typical,
            'recommended_platforms': preset.recommended_platforms
        }
    return jsonify(presets)


# ==================== 清理任务 ====================

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    """清理旧任务"""
    # 删除超过1小时的任务和文件
    now = datetime.now()
    to_remove = []
    
    for task_id, task in tasks.items():
        age = (now - task.created_at).total_seconds()
        if age > 3600:  # 1小时
            to_remove.append(task_id)
            
            # 删除文件
            try:
                if hasattr(task, 'input_path'):
                    Path(task.input_path).unlink(missing_ok=True)
                if task.result_path:
                    Path(task.result_path).unlink(missing_ok=True)
            except:
                pass
    
    for task_id in to_remove:
        del tasks[task_id]
    
    return jsonify({'cleaned': len(to_remove)})


# ==================== 启动 ====================

if __name__ == '__main__':
    print("🌐 启动 Dance Clipper Web 服务")
    print(f"   上传目录: {UPLOAD_FOLDER}")
    
    # 检查 GPU
    gpu = GPUAccelerator()
    gpu.print_info()
    
    # 启动服务
    app.run(host='0.0.0.0', port=5000, debug=True)
