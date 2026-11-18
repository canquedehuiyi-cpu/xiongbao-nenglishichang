#!/usr/bin/env python3
"""
学术论文检查工具
专门用于自动驾驶感知系统攻防研究论文的检查
"""

import re
import os
from typing import List, Dict, Tuple

class AcademicPaperChecker:
    """学术论文检查器"""
    
    def __init__(self):
        # 专业术语词典
        self.technical_terms = {
            # 点云相关
            'point cloud': ['点云', 'point cloud'],
            'PointNet': ['PointNet'],
            'PointNet++': ['PointNet++', 'PointNet plus plus'],
            'VoxelNet': ['VoxelNet'],
            'PV-RCNN': ['PV-RCNN'],
            
            # 安全攻击相关
            'backdoor attack': ['后门攻击', 'backdoor attack'],
            'clean-label attack': ['清洁标签攻击', 'clean-label attack'],
            'adversarial attack': ['对抗性攻击', 'adversarial attack'],
            'invisible backdoor': ['隐形后门', 'invisible backdoor'],
            
            # 自动驾驶相关
            'autonomous driving': ['自动驾驶', 'autonomous driving'],
            'perception system': ['感知系统', 'perception system'],
            'LiDAR': ['激光雷达', 'LiDAR'],
            '3D object detection': ['3D物体检测', '3D object detection'],
            
            # 深度学习相关
            'deep learning': ['深度学习', 'deep learning'],
            'neural network': ['神经网络', 'neural network'],
            'training from scratch': ['从头训练', 'training from scratch'],
            'model robustness': ['模型鲁棒性', 'model robustness']
        }
        
        # 常见错误模式
        self.common_errors = {
            'typo': [
                (r'\bteh\b', 'the'),
                (r'\bseperate\b', 'separate'),
                (r'\boccured\b', 'occurred'),
                (r'\brecieve\b', 'receive'),
                (r'\bdefinately\b', 'definitely'),
                (r'\bwierd\b', 'weird'),
                (r'\barguement\b', 'argument'),
                (r'\blabell?ing\b', 'labeling'),
            ],
            'academic_style': [
                (r'\bgot\b', 'obtained'),
                (r'\ba lot of\b', 'many'),
                (r'\bvery\b', 'highly'),
                (r'\bthing\b', 'aspect'),
                (r'\bstuff\b', 'material'),
            ]
        }
        
        # LaTeX常见问题
        self.latex_issues = [
            (r'\\cite\{[^}]+\}', '检查引用格式'),
            (r'\\ref\{[^}]+\}', '检查图表引用'),
            (r'\\label\{[^}]+\}', '检查标签定义'),
            (r'\$\$[^$]+\$\$', '检查数学公式'),
            (r'\\begin\{[^}]+\}', '检查环境开始'),
            (r'\\end\{[^}]+\}', '检查环境结束'),
        ]
    
    def check_latex_file(self, filepath: str) -> Dict:
        """检查LaTeX文件"""
        results = {
            'file_info': {},
            'errors': [],
            'warnings': [],
            'suggestions': [],
            'statistics': {}
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 基础统计
            results['file_info'] = {
                'filename': os.path.basename(filepath),
                'size_bytes': len(content),
                'lines': content.count('\n') + 1,
                'words': len(content.split())
            }
            
            # 检查常见错误
            self._check_common_errors(content, results)
            
            # 检查技术术语一致性
            self._check_technical_terms(content, results)
            
            # 检查LaTeX语法
            self._check_latex_syntax(content, results)
            
            # 检查学术写作风格
            self._check_academic_style(content, results)
            
            # 生成统计信息
            self._generate_statistics(results)
            
        except Exception as e:
            results['errors'].append(f"文件读取错误: {str(e)}")
        
        return results
    
    def _check_common_errors(self, content: str, results: Dict):
        """检查常见错误"""
        for error_type, patterns in self.common_errors.items():
            for pattern, correction in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    results['errors'].append({
                        'type': 'typo' if error_type == 'typo' else 'style',
                        'position': match.start(),
                        'error': match.group(),
                        'suggestion': correction,
                        'context': self._get_context(content, match.start(), match.end())
                    })
    
    def _check_technical_terms(self, content: str, results: Dict):
        """检查技术术语"""
        # 检查术语一致性（中英文混用）
        for term, variations in self.technical_terms.items():
            found_variations = []
            for variation in variations:
                if re.search(r'\b' + re.escape(variation) + r'\b', content, re.IGNORECASE):
                    found_variations.append(variation)
            
            if len(found_variations) > 1:
                results['warnings'].append({
                    'type': '术语不一致',
                    'term': term,
                    'found': found_variations,
                    'suggestion': f'建议统一使用"{found_variations[0]}"'
                })
    
    def _check_latex_syntax(self, content: str, results: Dict):
        """检查LaTeX语法"""
        # 检查未闭合的环境
        begin_matches = list(re.finditer(r'\\begin\{([^}]+)\}', content))
        end_matches = list(re.finditer(r'\\end\{([^}]+)\}', content))
        
        if len(begin_matches) != len(end_matches):
            results['warnings'].append({
                'type': 'LaTeX环境',
                'issue': 'begin和end数量不匹配',
                'suggestion': '检查所有环境是否正确闭合'
            })
        
        # 检查常见的LaTeX问题
        for pattern, issue in self.latex_issues:
            matches = re.finditer(pattern, content)
            for match in matches:
                results['warnings'].append({
                    'type': 'LaTeX格式',
                    'issue': issue,
                    'context': self._get_context(content, match.start(), match.end())
                })
    
    def _check_academic_style(self, content: str, results: Dict):
        """检查学术写作风格"""
        # 检查被动语态使用（学术写作中常用）
        passive_patterns = [
            r'is\s+[a-z]+ed\b',
            r'are\s+[a-z]+ed\b',
            r'was\s+[a-z]+ed\b',
            r'were\s+[a-z]+ed\b',
        ]
        
        for pattern in passive_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                # 这通常不是错误，但可以记录
                pass
    
    def _get_context(self, content: str, start: int, end: int, context_len: int = 50) -> str:
        """获取错误上下文"""
        context_start = max(0, start - context_len)
        context_end = min(len(content), end + context_len)
        return content[context_start:context_end]
    
    def _generate_statistics(self, results: Dict):
        """生成统计信息"""
        stats = {
            'total_errors': len(results['errors']),
            'total_warnings': len(results['warnings']),
            'total_suggestions': len(results['suggestions']),
            'error_types': {},
            'warning_types': {}
        }
        
        # 统计错误类型
        for error in results['errors']:
            error_type = error['type']
            stats['error_types'][error_type] = stats['error_types'].get(error_type, 0) + 1
        
        # 统计警告类型
        for warning in results['warnings']:
            warning_type = warning['type']
            stats['warning_types'][warning_type] = stats['warning_types'].get(warning_type, 0) + 1
        
        results['statistics'] = stats
    
    def generate_report(self, results: Dict) -> str:
        """生成检查报告"""
        report = []
        report.append("=" * 60)
        report.append("学术论文检查报告")
        report.append("=" * 60)
        report.append("")
        
        # 文件信息
        report.append("📄 文件信息:")
        for key, value in results['file_info'].items():
            report.append(f"  {key}: {value}")
        report.append("")
        
        # 统计信息
        stats = results['statistics']
        report.append("📊 统计信息:")
        report.append(f"  总错误数: {stats['total_errors']}")
        report.append(f"  总警告数: {stats['total_warnings']}")
        report.append("")
        
        # 错误详情
        if results['errors']:
            report.append("❌ 发现错误:")
            for i, error in enumerate(results['errors'][:10], 1):  # 只显示前10个
                report.append(f"  {i}. [{error['type']}] {error['error']} → {error['suggestion']}")
                report.append(f"     上下文: ...{error['context']}...")
            if len(results['errors']) > 10:
                report.append(f"  ... 还有{len(results['errors'])-10}个错误")
            report.append("")
        
        # 警告详情
        if results['warnings']:
            report.append("⚠️ 警告和建议:")
            for i, warning in enumerate(results['warnings'][:10], 1):
                report.append(f"  {i}. [{warning['type']}] {warning.get('issue', '')}")
                if 'suggestion' in warning:
                    report.append(f"     建议: {warning['suggestion']}")
            if len(results['warnings']) > 10:
                report.append(f"  ... 还有{len(results['warnings'])-10}个警告")
            report.append("")
        
        # 总体评估
        report.append("📈 总体评估:")
        if stats['total_errors'] == 0:
            report.append("  ✅ 基础错误检查通过")
        else:
            report.append(f"  ⚠️ 发现{stats['total_errors']}个基础错误需要修复")
        
        if stats['total_warnings'] < 5:
            report.append("  ✅ 格式和风格问题较少")
        else:
            report.append(f"  💡 有{stats['total_warnings']}个格式和风格建议")
        
        report.append("")
        report.append("=" * 60)
        
        return '\n'.join(report)


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python paper_checker.py <latex文件路径>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"错误: 文件不存在 - {filepath}")
        sys.exit(1)
    
    checker = AcademicPaperChecker()
    results = checker.check_latex_file(filepath)
    report = checker.generate_report(results)
    
    print(report)
    
    # 保存报告到文件
    report_file = f"{os.path.splitext(filepath)[0]}_check_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📝 详细报告已保存到: {report_file}")


if __name__ == "__main__":
    main()