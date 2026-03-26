"""
数据准备脚本 - TinyStories/WikiText-2
为TNN-Transformer Tiny模型准备训练数据

支持:
- TinyStories数据集 (短篇故事)
- WikiText-2数据集 (百科文本)
- 自定义BPE tokenizer训练

作者: AI Research Assistant
日期: 2026-03-18
"""

import os
import json
import pickle
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np

import torch
from torch.utils.data import Dataset

# 尝试导入datasets库
try:
    from datasets import load_dataset, Dataset as HFDataset
    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False
    print("警告: datasets库未安装，将使用本地数据")


# =============================================================================
# BPE Tokenizer (简化版)
# =============================================================================

class SimpleBPETokenizer:
    """简化的BPE Tokenizer"""
    
    def __init__(self, vocab_size: int = 10000, special_tokens: Optional[List[str]] = None):
        self.vocab_size = vocab_size
        self.special_tokens = special_tokens or ["<pad>", "<unk>", "<s>", "</s>"]
        self.pad_token = "<pad>"
        self.unk_token = "<unk>"
        self.bos_token = "<s>"
        self.eos_token = "</s>"
        
        self.vocab = {}
        self.inverse_vocab = {}
        self.merges = []
        
    def train(self, texts: List[str], min_frequency: int = 2):
        """训练BPE tokenizer"""
        print(f"训练BPE tokenizer (vocab_size={self.vocab_size})...")
        
        # 初始化词表 (字符级别)
        word_freqs = {}
        for text in texts:
            words = text.split()
            for word in words:
                # 将单词分解为字符序列
                chars = tuple(word) + ('</w>',)
                word_freqs[chars] = word_freqs.get(chars, 0) + 1
        
        # 初始化词表
        vocab_set = set()
        for word in word_freqs:
            vocab_set.update(word)
        
        # 添加特殊token
        for token in self.special_tokens:
            vocab_set.add(token)
        
        vocab_list = list(vocab_set)
        self.vocab = {token: i for i, token in enumerate(vocab_list)}
        
        # BPE合并 (简化版)
        num_merges = min(self.vocab_size - len(vocab_list), 1000)
        
        for i in range(num_merges):
            if len(self.vocab) >= self.vocab_size:
                break
            
            # 统计pair频率
            pairs = {}
            for word, freq in word_freqs.items():
                for j in range(len(word) - 1):
                    pair = (word[j], word[j + 1])
                    pairs[pair] = pairs.get(pair, 0) + freq
            
            if not pairs:
                break
            
            # 找到最高频pair
            best_pair = max(pairs, key=pairs.get)
            
            if pairs[best_pair] < min_frequency:
                break
            
            # 合并pair
            new_token = best_pair[0] + best_pair[1]
            if new_token not in self.vocab:
                self.vocab[new_token] = len(self.vocab)
            
            self.merges.append(best_pair)
            
            # 更新word_freqs
            new_word_freqs = {}
            for word, freq in word_freqs.items():
                new_word = []
                i = 0
                while i < len(word):
                    if i < len(word) - 1 and (word[i], word[i + 1]) == best_pair:
                        new_word.append(new_token)
                        i += 2
                    else:
                        new_word.append(word[i])
                        i += 1
                new_word_freqs[tuple(new_word)] = freq
            word_freqs = new_word_freqs
        
        self.inverse_vocab = {i: token for token, i in self.vocab.items()}
        print(f"  词表大小: {len(self.vocab)}")
        
    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        """编码文本"""
        # 简化的编码 (字符级别 + 合并)
        tokens = []
        
        if add_special_tokens:
            tokens.append(self.vocab.get(self.bos_token, 2))
        
        words = text.split()
        for word in words:
            chars = list(word) + ['</w>']
            # 应用合并
            for merge in self.merges:
                new_chars = []
                i = 0
                while i < len(chars):
                    if i < len(chars) - 1 and (chars[i], chars[i + 1]) == merge:
                        new_chars.append(merge[0] + merge[1])
                        i += 2
                    else:
                        new_chars.append(chars[i])
                        i += 1
                chars = new_chars
            
            for char in chars:
                tokens.append(self.vocab.get(char, self.vocab.get(self.unk_token, 1)))
        
        if add_special_tokens:
            tokens.append(self.vocab.get(self.eos_token, 3))
        
        return tokens
    
    def decode(self, token_ids: List[int], skip_special_tokens: bool = True) -> str:
        """解码token序列"""
        special_ids = {
            self.vocab.get(self.pad_token, 0),
            self.vocab.get(self.unk_token, 1),
            self.vocab.get(self.bos_token, 2),
            self.vocab.get(self.eos_token, 3),
        }
        
        chars = []
        for token_id in token_ids:
            if skip_special_tokens and token_id in special_ids:
                continue
            token = self.inverse_vocab.get(token_id, self.unk_token)
            if token.endswith('</w>'):
                chars.append(token[:-4] + ' ')
            else:
                chars.append(token)
        
        return ''.join(chars).strip()
    
    def save(self, save_dir: str):
        """保存tokenizer"""
        os.makedirs(save_dir, exist_ok=True)
        
        data = {
            'vocab': self.vocab,
            'merges': self.merges,
            'special_tokens': self.special_tokens,
            'vocab_size': self.vocab_size,
        }
        
        with open(os.path.join(save_dir, 'tokenizer.pkl'), 'wb') as f:
            pickle.dump(data, f)
        
        # 同时保存为json便于查看
        json_data = {k: v for k, v in data.items() if k != 'merges'}
        json_data['merges'] = [list(m) for m in self.merges[:100]]  # 只保存前100个合并
        with open(os.path.join(save_dir, 'tokenizer.json'), 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"Tokenizer已保存至: {save_dir}")
    
    @classmethod
    def load(cls, load_dir: str):
        """加载tokenizer"""
        with open(os.path.join(load_dir, 'tokenizer.pkl'), 'rb') as f:
            data = pickle.load(f)
        
        tokenizer = cls(vocab_size=data['vocab_size'], special_tokens=data['special_tokens'])
        tokenizer.vocab = data['vocab']
        tokenizer.merges = data['merges']
        tokenizer.inverse_vocab = {i: token for token, i in tokenizer.vocab.items()}
        
        return tokenizer


# =============================================================================
# 数据集类
# =============================================================================

class TextDataset(Dataset):
    """文本数据集"""
    
    def __init__(self, tokenized_texts: List[List[int]], max_length: int = 512):
        self.tokenized_texts = tokenized_texts
        self.max_length = max_length
        
    def __len__(self):
        return len(self.tokenized_texts)
    
    def __getitem__(self, idx):
        tokens = self.tokenized_texts[idx]
        
        # 截断或填充
        if len(tokens) > self.max_length:
            tokens = tokens[:self.max_length]
        else:
            tokens = tokens + [0] * (self.max_length - len(tokens))
        
        return torch.tensor(tokens, dtype=torch.long)


class TinyStoriesDataset(Dataset):
    """TinyStories数据集"""
    
    def __init__(self, data_path: str, tokenizer, max_length: int = 512):
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # 加载数据
        with open(data_path, 'r', encoding='utf-8') as f:
            if data_path.endswith('.json'):
                self.raw_texts = json.load(f)
            else:
                self.raw_texts = [line.strip() for line in f if line.strip()]
        
        print(f"加载了 {len(self.raw_texts)} 条文本")
        
    def __len__(self):
        return len(self.raw_texts)
    
    def __getitem__(self, idx):
        text = self.raw_texts[idx]
        if isinstance(text, dict):
            text = text.get('text', text.get('story', str(text)))
        
        tokens = self.tokenizer.encode(text, add_special_tokens=True)
        
        # 截断或填充
        if len(tokens) > self.max_length:
            tokens = tokens[:self.max_length]
        else:
            tokens = tokens + [0] * (self.max_length - len(tokens))
        
        return torch.tensor(tokens, dtype=torch.long)


# =============================================================================
# 数据准备函数
# =============================================================================

def download_tinystories(save_dir: str = "./data/tinystories", max_samples: int = 500000) -> str:
    """下载TinyStories数据集"""
    os.makedirs(save_dir, exist_ok=True)
    
    if HAS_DATASETS:
        print(f"下载TinyStories数据集 (max_samples={max_samples})...")
        dataset = load_dataset("roneneldan/TinyStories", split="train", streaming=True)
        
        texts = []
        for i, example in enumerate(dataset):
            if i >= max_samples:
                break
            texts.append(example['text'])
            if (i + 1) % 10000 == 0:
                print(f"  已下载 {i + 1} 条样本")
        
        # 保存
        data_path = os.path.join(save_dir, "train.json")
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(texts, f, ensure_ascii=False)
        
        print(f"TinyStories数据已保存至: {data_path}")
        return data_path
    else:
        # 创建示例数据
        print("创建示例TinyStories数据...")
        sample_stories = [
            "Once upon a time, there was a little girl named Lily.",
            "She loved to play in the garden every day.",
            "One sunny morning, she found a small red ball.",
            "Lily played with the ball all afternoon.",
            "At night, she went to bed and dreamed of playing.",
        ] * 1000  # 重复生成示例数据
        
        data_path = os.path.join(save_dir, "train_sample.json")
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(sample_stories, f, ensure_ascii=False)
        
        print(f"示例数据已保存至: {data_path}")
        return data_path


def download_wikitext2(save_dir: str = "./data/wikitext2") -> Tuple[str, str]:
    """下载WikiText-2数据集"""
    os.makedirs(save_dir, exist_ok=True)
    
    if HAS_DATASETS:
        print("下载WikiText-2数据集...")
        dataset = load_dataset("wikitext", "wikitext-2-raw-v1")
        
        train_texts = [text for text in dataset['train']['text'] if text.strip()]
        val_texts = [text for text in dataset['validation']['text'] if text.strip()]
        
        train_path = os.path.join(save_dir, "train.txt")
        val_path = os.path.join(save_dir, "valid.txt")
        
        with open(train_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(train_texts))
        
        with open(val_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(val_texts))
        
        print(f"WikiText-2数据已保存")
        return train_path, val_path
    else:
        # 创建示例数据
        print("创建示例WikiText数据...")
        sample_texts = [
            "Natural language processing is a subfield of linguistics, computer science, and artificial intelligence.",
            "It is concerned with the interactions between computers and human language.",
            "The goal is to enable computers to understand, interpret, and generate human language.",
        ] * 500
        
        train_path = os.path.join(save_dir, "train_sample.txt")
        val_path = os.path.join(save_dir, "valid_sample.txt")
        
        with open(train_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sample_texts[:700]))
        
        with open(val_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sample_texts[700:]))
        
        return train_path, val_path


def prepare_data(
    dataset_name: str = "tinystories",
    data_dir: str = "./data",
    vocab_size: int = 10000,
    max_length: int = 512,
    max_samples: int = 500000,
    split_ratio: float = 0.9,
) -> Dict[str, str]:
    """
    准备训练数据
    
    Args:
        dataset_name: 数据集名称 (tinystories 或 wikitext2)
        data_dir: 数据保存目录
        vocab_size: 词表大小
        max_length: 最大序列长度
        max_samples: 最大样本数
        split_ratio: 训练/验证分割比例
    
    Returns:
        包含paths和vocab_size的字典
    """
    print(f"\n{'='*60}")
    print(f"准备数据集: {dataset_name}")
    print(f"{'='*60}\n")
    
    # 1. 下载/加载数据
    if dataset_name == "tinystories":
        data_path = download_tinystories(
            save_dir=os.path.join(data_dir, "tinystories"),
            max_samples=max_samples
        )
        
        # 加载文本
        with open(data_path, 'r', encoding='utf-8') as f:
            texts = json.load(f)
    
    elif dataset_name == "wikitext2":
        train_path, val_path = download_wikitext2(
            save_dir=os.path.join(data_dir, "wikitext2")
        )
        
        # 加载文本
        with open(train_path, 'r', encoding='utf-8') as f:
            train_texts = [line.strip() for line in f if line.strip()]
        with open(val_path, 'r', encoding='utf-8') as f:
            val_texts = [line.strip() for line in f if line.strip()]
        
        texts = train_texts + val_texts
    
    else:
        raise ValueError(f"不支持的数据集: {dataset_name}")
    
    print(f"总文本数: {len(texts)}")
    
    # 2. 分割训练/验证集
    random.seed(42)
    random.shuffle(texts)
    
    split_idx = int(len(texts) * split_ratio)
    train_texts = texts[:split_idx]
    val_texts = texts[split_idx:]
    
    print(f"训练集: {len(train_texts)} 条")
    print(f"验证集: {len(val_texts)} 条")
    
    # 3. 训练tokenizer
    tokenizer_dir = os.path.join(data_dir, "tokenizer")
    
    if os.path.exists(os.path.join(tokenizer_dir, "tokenizer.pkl")):
        print("\n加载已存在的tokenizer...")
        tokenizer = SimpleBPETokenizer.load(tokenizer_dir)
    else:
        print("\n训练tokenizer...")
        tokenizer = SimpleBPETokenizer(vocab_size=vocab_size)
        tokenizer.train(train_texts[:min(50000, len(train_texts))], min_frequency=2)
        tokenizer.save(tokenizer_dir)
    
    # 4. Tokenize并保存
    print("\nTokenizing训练集...")
    train_tokens = [tokenizer.encode(text, add_special_tokens=True) for text in train_texts]
    
    print("Tokenizing验证集...")
    val_tokens = [tokenizer.encode(text, add_special_tokens=True) for text in val_texts]
    
    # 5. 保存处理后的数据
    processed_dir = os.path.join(data_dir, "processed", dataset_name)
    os.makedirs(processed_dir, exist_ok=True)
    
    train_path = os.path.join(processed_dir, "train.pt")
    val_path = os.path.join(processed_dir, "val.pt")
    
    torch.save(train_tokens, train_path)
    torch.save(val_tokens, val_path)
    
    print(f"\n训练数据已保存至: {train_path}")
    print(f"验证数据已保存至: {val_path}")
    
    # 保存元数据
    meta = {
        'dataset_name': dataset_name,
        'vocab_size': len(tokenizer.vocab),
        'max_length': max_length,
        'train_samples': len(train_texts),
        'val_samples': len(val_texts),
    }
    
    with open(os.path.join(processed_dir, "meta.json"), 'w') as f:
        json.dump(meta, f, indent=2)
    
    print(f"\n{'='*60}")
    print("数据准备完成!")
    print(f"词表大小: {len(tokenizer.vocab)}")
    print(f"训练样本: {len(train_texts)}")
    print(f"验证样本: {len(val_texts)}")
    print(f"{'='*60}\n")
    
    return {
        'train_path': train_path,
        'val_path': val_path,
        'tokenizer_dir': tokenizer_dir,
        'vocab_size': len(tokenizer.vocab),
        'max_length': max_length,
    }


def load_prepared_data(data_dir: str = "./data/processed/tinystories") -> Tuple[Dataset, Dataset, SimpleBPETokenizer]:
    """加载已准备好的数据"""
    # 加载元数据
    with open(os.path.join(data_dir, "meta.json"), 'r') as f:
        meta = json.load(f)
    
    # 加载tokenizer
    tokenizer_dir = os.path.join(data_dir, "..", "..", "tokenizer")
    tokenizer = SimpleBPETokenizer.load(tokenizer_dir)
    
    # 加载数据
    train_tokens = torch.load(os.path.join(data_dir, "train.pt"))
    val_tokens = torch.load(os.path.join(data_dir, "val.pt"))
    
    train_dataset = TextDataset(train_tokens, max_length=meta['max_length'])
    val_dataset = TextDataset(val_tokens, max_length=meta['max_length'])
    
    return train_dataset, val_dataset, tokenizer


# =============================================================================
# 主函数
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="准备TNN-Transformer训练数据")
    parser.add_argument("--dataset", type=str, default="tinystories", 
                        choices=["tinystories", "wikitext2"],
                        help="数据集名称")
    parser.add_argument("--data_dir", type=str, default="./data",
                        help="数据保存目录")
    parser.add_argument("--vocab_size", type=int, default=10000,
                        help="词表大小")
    parser.add_argument("--max_length", type=int, default=512,
                        help="最大序列长度")
    parser.add_argument("--max_samples", type=int, default=100000,
                        help="最大样本数")
    
    args = parser.parse_args()
    
    # 准备数据
    result = prepare_data(
        dataset_name=args.dataset,
        data_dir=args.data_dir,
        vocab_size=args.vocab_size,
        max_length=args.max_length,
        max_samples=args.max_samples,
    )
    
    # 测试tokenizer
    print("\n测试tokenizer...")
    tokenizer = SimpleBPETokenizer.load(result['tokenizer_dir'])
    
    sample_text = "Once upon a time, there was a little girl."
    encoded = tokenizer.encode(sample_text)
    decoded = tokenizer.decode(encoded)
    
    print(f"  原文: {sample_text}")
    print(f"  编码: {encoded[:20]}...")
    print(f"  解码: {decoded}")
    print(f"  词表大小: {len(tokenizer.vocab)}")
    
    print("\n✓ 数据准备完成!")
