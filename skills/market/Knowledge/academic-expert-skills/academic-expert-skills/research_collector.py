#!/usr/bin/env python3
"""
学术资源收集工具
专门收集自动驾驶感知系统攻防研究的相关资源
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any

class ResearchResourceCollector:
    """学术资源收集器"""
    
    def __init__(self):
        self.resources_file = "academic_resources.json"
        self.resources = self._load_resources()
        
        # 研究方向关键词
        self.research_keywords = [
            # 核心研究方向
            "point cloud backdoor attack",
            "clean-label attack point cloud",
            "invisible backdoor 3D",
            "autonomous driving perception security",
            
            # 相关技术
            "PointNet backdoor",
            "3D object detection adversarial",
            "LiDAR perception attack",
            "deep learning security autonomous driving",
            
            # 基础理论
            "backdoor attack survey",
            "adversarial machine learning 3D",
            "model robustness point cloud",
            "secure deep learning"
        ]
    
    def _load_resources(self) -> Dict:
        """加载现有资源"""
        if os.path.exists(self.resources_file):
            try:
                with open(self.resources_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self._create_empty_resources()
        return self._create_empty_resources()
    
    def _create_empty_resources(self) -> Dict:
        """创建空的资源结构"""
        return {
            "research_field": "自动驾驶感知系统攻防研究 - 点云后门攻击",
            "last_updated": datetime.now().isoformat(),
            "papers": [],
            "datasets": [],
            "tools": [],
            "conferences": [],
            "research_groups": [],
            "update_log": []
        }
    
    def _save_resources(self):
        """保存资源到文件"""
        self.resources["last_updated"] = datetime.now().isoformat()
        with open(self.resources_file, 'w', encoding='utf-8') as f:
            json.dump(self.resources, f, ensure_ascii=False, indent=2)
    
    def add_paper(self, title: str, authors: List[str], venue: str, year: int,
                  url: str, abstract: str = "", keywords: List[str] = None):
        """添加论文"""
        paper = {
            "id": f"paper_{len(self.resources['papers']) + 1:03d}",
            "title": title,
            "authors": authors,
            "venue": venue,
            "year": year,
            "url": url,
            "abstract": abstract,
            "keywords": keywords or [],
            "added_date": datetime.now().isoformat(),
            "relevance_score": self._calculate_relevance(title, abstract, keywords)
        }
        
        self.resources["papers"].append(paper)
        self._log_update(f"添加论文: {title}")
        self._save_resources()
        
        return paper
    
    def add_dataset(self, name: str, description: str, url: str, 
                   size: str = "", format: str = "", tasks: List[str] = None):
        """添加数据集"""
        dataset = {
            "id": f"dataset_{len(self.resources['datasets']) + 1:03d}",
            "name": name,
            "description": description,
            "url": url,
            "size": size,
            "format": format,
            "tasks": tasks or [],
            "added_date": datetime.now().isoformat()
        }
        
        self.resources["datasets"].append(dataset)
        self._log_update(f"添加数据集: {name}")
        self._save_resources()
        
        return dataset
    
    def add_tool(self, name: str, description: str, url: str, 
                language: str = "", purpose: str = ""):
        """添加工具"""
        tool = {
            "id": f"tool_{len(self.resources['tools']) + 1:03d}",
            "name": name,
            "description": description,
            "url": url,
            "language": language,
            "purpose": purpose,
            "added_date": datetime.now().isoformat()
        }
        
        self.resources["tools"].append(tool)
        self._log_update(f"添加工具: {name}")
        self._save_resources()
        
        return tool
    
    def add_conference(self, name: str, abbreviation: str, url: str,
                      deadline: str = "", topics: List[str] = None):
        """添加会议"""
        conference = {
            "id": f"conf_{len(self.resources['conferences']) + 1:03d}",
            "name": name,
            "abbreviation": abbreviation,
            "url": url,
            "deadline": deadline,
            "topics": topics or [],
            "added_date": datetime.now().isoformat()
        }
        
        self.resources["conferences"].append(conference)
        self._log_update(f"添加会议: {name}")
        self._save_resources()
        
        return conference
    
    def add_research_group(self, name: str, institution: str, url: str,
                          focus: str = "", key_people: List[str] = None):
        """添加研究组"""
        group = {
            "id": f"group_{len(self.resources['research_groups']) + 1:03d}",
            "name": name,
            "institution": institution,
            "url": url,
            "focus": focus,
            "key_people": key_people or [],
            "added_date": datetime.now().isoformat()
        }
        
        self.resources["research_groups"].append(group)
        self._log_update(f"添加研究组: {name}")
        self._save_resources()
        
        return group
    
    def _calculate_relevance(self, title: str, abstract: str, keywords: List[str]) -> int:
        """计算论文相关性分数"""
        text = f"{title} {abstract} {' '.join(keywords or [])}".lower()
        
        score = 0
        for keyword in self.research_keywords:
            if keyword.lower() in text:
                score += 1
        
        return min(score, 10)  # 最高10分
    
    def _log_update(self, action: str):
        """记录更新日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action
        }
        self.resources["update_log"].append(log_entry)
    
    def get_relevant_papers(self, min_score: int = 3) -> List[Dict]:
        """获取相关性高的论文"""
        relevant = []
        for paper in self.resources["papers"]:
            if paper.get("relevance_score", 0) >= min_score:
                relevant.append(paper)
        
        # 按相关性分数排序
        relevant.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return relevant
    
    def generate_research_report(self) -> str:
        """生成研究资源报告"""
        report = []
        report.append("=" * 70)
        report.append("自动驾驶感知系统攻防研究 - 学术资源报告")
        report.append("=" * 70)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"最后更新: {self.resources.get('last_updated', '未知')}")
        report.append("")
        
        # 论文统计
        total_papers = len(self.resources["papers"])
        relevant_papers = len(self.get_relevant_papers(min_score=3))
        
        report.append("📚 论文资源:")
        report.append(f"  总论文数: {total_papers}")
        report.append(f"  高相关论文: {relevant_papers}")
        report.append("")
        
        # 高相关论文列表
        if relevant_papers > 0:
            report.append("🎯 高相关性论文:")
            for paper in self.get_relevant_papers(min_score=5)[:5]:  # 显示前5个
                report.append(f"  • {paper['title']}")
                report.append(f"    作者: {', '.join(paper['authors'][:3])}{'等' if len(paper['authors']) > 3 else ''}")
                report.append(f"    会议/期刊: {paper['venue']} ({paper['year']})")
                report.append(f"    相关性分数: {paper.get('relevance_score', 'N/A')}/10")
                report.append("")
        
        # 数据集
        if self.resources["datasets"]:
            report.append("🗃️ 相关数据集:")
            for dataset in self.resources["datasets"][:3]:
                report.append(f"  • {dataset['name']}")
                report.append(f"    描述: {dataset['description'][:100]}...")
                report.append("")
        
        # 工具
        if self.resources["tools"]:
            report.append("🛠️ 相关工具:")
            for tool in self.resources["tools"][:3]:
                report.append(f"  • {tool['name']}")
                report.append(f"    用途: {tool['purpose']}")
                report.append("")
        
        # 研究方向关键词
        report.append("🔍 研究方向关键词:")
        for i, keyword in enumerate(self.research_keywords[:10], 1):
            report.append(f"  {i}. {keyword}")
        
        report.append("")
        report.append("=" * 70)
        
        return '\n'.join(report)
    
    def initialize_with_basic_resources(self):
        """初始化基础资源"""
        print("正在初始化基础学术资源...")
        
        # 添加基础论文
        self.add_paper(
            title="PointNet: Deep Learning on Point Sets for 3D Classification and Segmentation",
            authors=["Charles R. Qi", "Hao Su", "Kaichun Mo", "Leonidas J. Guibas"],
            venue="CVPR",
            year=2017,
            url="https://arxiv.org/abs/1612.00593",
            abstract="We design a novel type of neural network that directly consumes point clouds...",
            keywords=["point cloud", "deep learning", "3D classification", "segmentation"]
        )
        
        self.add_paper(
            title="BadNets: Identifying Vulnerabilities in the Machine Learning Model Supply Chain",
            authors=["Tianyu Gu", "Brendan Dolan-Gavitt", "Siddharth Garg"],
            venue="arXiv",
            year=2017,
            url="https://arxiv.org/abs/1708.06733",
            abstract="Deep learning models are vulnerable to backdoor attacks...",
            keywords=["backdoor attack", "machine learning security", "supply chain"]
        )
        
        self.add_paper(
            title="Clean-Label Backdoor Attacks",
            authors=["Alexander Turner", "Dimitris Tsipras", "Aleksander Madry"],
            venue="ICLR",
            year=2019,
            url="https://arxiv.org/abs/1905.03809",
            abstract="We study clean-label backdoor attacks where the adversary does not control the labeling process...",
            keywords=["clean-label attack", "backdoor", "adversarial machine learning"]
        )
        
        # 添加数据集
        self.add_dataset(
            name="ModelNet40",
            description="A large-scale 3D CAD model dataset containing 12,311 models from 40 categories",
            url="http://modelnet.cs.princeton.edu/",
            size="~1.5GB",
            format=".off files",
            tasks=["3D classification", "object recognition"]
        )
        
        self.add_dataset(
            name="ShapeNet",
            description="A richly-annotated, large-scale dataset of 3D shapes",
            url="https://www.shapenet.org/",
            size="~1TB",
            format="Various 3D formats",
            tasks=["3D reconstruction", "segmentation", "classification"]
        )
        
        # 添加工具
        self.add_tool(
            name="PointNet PyTorch Implementation",
            description="PyTorch implementation of PointNet for point cloud classification and segmentation",
            url="https://github.com/charlesq34/pointnet",
            language="Python",
            purpose="Point cloud deep learning"
        )
        
        # 添加会议
        self.add_conference(
            name="IEEE/CVF Conference on Computer Vision and Pattern Recognition",
            abbreviation="CVPR",
            url="https://cvpr.thecvf.com/",
            topics=["computer vision", "deep learning", "3D vision", "security"]
        )
        
        self.add_conference(
            name="International Conference on Learning Representations",
            abbreviation="ICLR",
            url="https://iclr.cc/",
            topics=["deep learning", "representation learning", "security"]
        )
        
        print("基础资源初始化完成！")
        print(f"已添加 {len(self.resources['papers'])} 篇论文")
        print(f"已添加 {len(self.resources['datasets'])} 个数据集")


def main():
    """主函数"""
    collector = ResearchResourceCollector()
    
    # 检查是否已有资源，如果没有则初始化
    if len(collector.resources["papers"]) == 0:
        collector.initialize_with_basic_resources()
    
    # 生成报告
    report = collector.generate_research_report()
    print(report)
    
    # 保存报告到文件
    report_file = "research_resources_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📋 详细报告已保存到: {report_file}")
    print(f"📊 资源数据库: {collector.resources_file}")


if __name__ == "__main__":
    main()