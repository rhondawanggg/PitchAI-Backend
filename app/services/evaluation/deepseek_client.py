# File: backend/app/services/evaluation/deepseek_client.py

import openai
from typing import Dict, List, Any
import json
import asyncio
from ...core.config.settings import settings

class DeepSeekClient:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )

    async def evaluate_business_plan(self, document_text: str) -> Dict[str, Any]:
        """Main evaluation function that processes a business plan"""
        try:
            # Define the standard evaluation dimensions
            dimensions = {
                "团队能力": {
                    "max_score": 30,
                    "sub_dimensions": {
                        "核心团队背景": 10,
                        "团队完整性": 10,
                        "团队执行力": 10
                    }
                },
                "产品&技术": {
                    "max_score": 20,
                    "sub_dimensions": {
                        "技术创新性": 8,
                        "产品成熟度": 6,
                        "研发能力": 6
                    }
                },
                "市场前景": {
                    "max_score": 20,
                    "sub_dimensions": {
                        "市场空间": 8,
                        "竞争分析": 6,
                        "市场策略": 6
                    }
                },
                "商业模式": {
                    "max_score": 20,
                    "sub_dimensions": {
                        "盈利模式": 8,
                        "运营模式": 6,
                        "发展模式": 6
                    }
                },
                "财务情况": {
                    "max_score": 10,
                    "sub_dimensions": {
                        "财务状况": 5,
                        "融资需求": 5
                    }
                }
            }

            # Evaluate each dimension
            evaluation_results = {}
            missing_info = []

            for dimension_key, dimension_config in dimensions.items():
                print(f"🔍 Evaluating dimension: {dimension_key}")

                dimension_result = await self._evaluate_dimension(
                    dimension_key,
                    dimension_config,
                    document_text
                )

                evaluation_results[dimension_key] = dimension_result

                # Collect missing information
                if "missing_info" in dimension_result:
                    missing_info.extend(dimension_result["missing_info"])

            # Calculate total score
            total_score = sum(result["score"] for result in evaluation_results.values())

            return {
                "dimensions": evaluation_results,
                "total_score": total_score,
                "missing_information": missing_info,
                "evaluation_summary": self._generate_summary(total_score, evaluation_results)
            }

        except Exception as e:
            print(f"❌ Evaluation failed: {str(e)}")
            # Return fallback evaluation
            return self._get_fallback_evaluation()

    async def _evaluate_dimension(
        self,
        dimension: str,
        config: Dict,
        document_text: str
    ) -> Dict[str, Any]:
        """Evaluate a specific dimension using DeepSeek API"""
        try:
            prompt = self._get_dimension_prompt(dimension, config, document_text)

            print(f"🤖 Calling DeepSeek API for dimension: {dimension}")

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的项目评审专家，负责评估商业计划书。请严格按照JSON格式返回评估结果。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )

            # Parse the response
            response_content = response.choices[0].message.content.strip()

            # Clean up the response (remove markdown code blocks if present)
            if response_content.startswith("```json"):
                response_content = response_content.replace("```json", "").replace("```", "").strip()

            try:
                result = json.loads(response_content)
                print(f"✅ Successfully evaluated {dimension}: {result['score']}/{config['max_score']}")
                return result
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parse error for {dimension}: {str(e)}")
                print(f"Raw response: {response_content}")
                return self._get_fallback_dimension_evaluation(dimension, config)

        except Exception as e:
            print(f"❌ API call failed for {dimension}: {str(e)}")
            return self._get_fallback_dimension_evaluation(dimension, config)

    def _get_dimension_prompt(self, dimension: str, config: Dict, document_text: str) -> str:
        """Generate evaluation prompt for specific dimension"""

        prompts = {
            "团队能力": f"""
请分析以下商业计划书中的团队能力维度，总分{config['max_score']}分。

评分标准：
- 核心团队背景 (10分): 核心成员的行业经验、技术背景、管理经验
- 团队完整性 (10分): 核心岗位配置完整性、团队规模合理性、团队结构
- 团队执行力 (10分): 过往项目成就、执行经验、资源整合能力

商业计划书内容：
{document_text[:3000]}

请返回JSON格式的评估结果：
{{
    "score": 总分数值,
    "max_score": {config['max_score']},
    "comments": "详细评价，100字以内",
    "sub_dimensions": [
        {{"sub_dimension": "核心团队背景", "score": 分数, "max_score": 10, "comments": "评价"}},
        {{"sub_dimension": "团队完整性", "score": 分数, "max_score": 10, "comments": "评价"}},
        {{"sub_dimension": "团队执行力", "score": 分数, "max_score": 10, "comments": "评价"}}
    ],
    "missing_info": [
        {{"type": "缺失信息类型", "description": "具体描述缺失的团队信息"}}
    ]
}}
""",
            "产品&技术": f"""
请分析以下商业计划书中的产品技术能力维度，总分{config['max_score']}分。

评分标准：
- 技术创新性 (8分): 技术先进性、专利/IP保护、技术壁垒
- 产品成熟度 (6分): 产品完成度、技术可行性、产品迭代能力
- 研发能力 (6分): 研发投入、技术团队实力、创新能力

商业计划书内容：
{document_text[:3000]}

请返回JSON格式的评估结果：
{{
    "score": 总分数值,
    "max_score": {config['max_score']},
    "comments": "详细评价，100字以内",
    "sub_dimensions": [
        {{"sub_dimension": "技术创新性", "score": 分数, "max_score": 8, "comments": "评价"}},
        {{"sub_dimension": "产品成熟度", "score": 分数, "max_score": 6, "comments": "评价"}},
        {{"sub_dimension": "研发能力", "score": 分数, "max_score": 6, "comments": "评价"}}
    ],
    "missing_info": [
        {{"type": "缺失信息类型", "description": "具体描述缺失的技术信息"}}
    ]
}}
""",
            "市场前景": f"""
请分析以下商业计划书中的市场竞争力维度，总分{config['max_score']}分。

评分标准：
- 市场空间 (8分): 市场规模、市场增长率、市场潜力
- 竞争分析 (6分): 竞争格局、竞争优势、市场定位
- 市场策略 (6分): 营销策略、渠道建设、品牌建设

商业计划书内容：
{document_text[:3000]}

请返回JSON格式的评估结果：
{{
    "score": 总分数值,
    "max_score": {config['max_score']},
    "comments": "详细评价，100字以内",
    "sub_dimensions": [
        {{"sub_dimension": "市场空间", "score": 分数, "max_score": 8, "comments": "评价"}},
        {{"sub_dimension": "竞争分析", "score": 分数, "max_score": 6, "comments": "评价"}},
        {{"sub_dimension": "市场策略", "score": 分数, "max_score": 6, "comments": "评价"}}
    ],
    "missing_info": [
        {{"type": "缺失信息类型", "description": "具体描述缺失的市场信息"}}
    ]
}}
""",
            "商业模式": f"""
请分析以下商业计划书中的商业模式维度，总分{config['max_score']}分。

评分标准：
- 盈利模式 (8分): 收入来源、成本结构、毛利率
- 运营模式 (6分): 运营效率、资源利用、流程设计
- 发展模式 (6分): 扩张策略、资源整合、风险控制

商业计划书内容：
{document_text[:3000]}

请返回JSON格式的评估结果：
{{
    "score": 总分数值,
    "max_score": {config['max_score']},
    "comments": "详细评价，100字以内",
    "sub_dimensions": [
        {{"sub_dimension": "盈利模式", "score": 分数, "max_score": 8, "comments": "评价"}},
        {{"sub_dimension": "运营模式", "score": 分数, "max_score": 6, "comments": "评价"}},
        {{"sub_dimension": "发展模式", "score": 分数, "max_score": 6, "comments": "评价"}}
    ],
    "missing_info": [
        {{"type": "缺失信息类型", "description": "具体描述缺失的商业模式信息"}}
    ]
}}
""",
            "财务情况": f"""
请分析以下商业计划书中的财务情况维度，总分{config['max_score']}分。

评分标准：
- 财务状况 (5分): 收入情况、成本控制、现金流
- 融资需求 (5分): 资金需求、融资计划、估值合理性

商业计划书内容：
{document_text[:3000]}

请返回JSON格式的评估结果：
{{
    "score": 总分数值,
    "max_score": {config['max_score']},
    "comments": "详细评价，100字以内",
    "sub_dimensions": [
        {{"sub_dimension": "财务状况", "score": 分数, "max_score": 5, "comments": "评价"}},
        {{"sub_dimension": "融资需求", "score": 分数, "max_score": 5, "comments": "评价"}}
    ],
    "missing_info": [
        {{"type": "缺失信息类型", "description": "具体描述缺失的财务信息"}}
    ]
}}
"""
        }

        return prompts.get(dimension, "")

    def _get_fallback_dimension_evaluation(self, dimension: str, config: Dict) -> Dict[str, Any]:
        """Return fallback evaluation when API fails"""
        return {
            "score": config['max_score'] * 0.6,  # Give 60% as default
            "max_score": config['max_score'],
            "comments": f"{dimension}评估暂时无法完成，请人工评审",
            "sub_dimensions": [
                {
                    "sub_dimension": sub_name,
                    "score": sub_max * 0.6,
                    "max_score": sub_max,
                    "comments": "待人工评审"
                }
                for sub_name, sub_max in config['sub_dimensions'].items()
            ],
            "missing_info": [
                {
                    "type": "AI评估失败",
                    "description": f"{dimension}维度需要人工评审"
                }
            ]
        }

    def _get_fallback_evaluation(self) -> Dict[str, Any]:
        """Return fallback evaluation when entire process fails"""
        dimensions = {
            "团队能力": {"score": 18, "max_score": 30, "comments": "需要人工评审"},
            "产品&技术": {"score": 12, "max_score": 20, "comments": "需要人工评审"},
            "市场前景": {"score": 12, "max_score": 20, "comments": "需要人工评审"},
            "商业模式": {"score": 12, "max_score": 20, "comments": "需要人工评审"},
            "财务情况": {"score": 6, "max_score": 10, "comments": "需要人工评审"}
        }

        return {
            "dimensions": dimensions,
            "total_score": 60,
            "missing_information": [
                {"type": "AI评估失败", "description": "自动评估失败，需要人工评审"}
            ],
            "evaluation_summary": "自动评估失败，建议人工评审"
        }

    def _generate_summary(self, total_score: float, dimensions: Dict) -> str:
        """Generate evaluation summary based on total score"""
        if total_score >= 80:
            return "优秀项目，可考虑给予企业工位"
        elif total_score >= 60:
            return "符合基本入孵条件，可注册在工研院"
        else:
            return "暂不符合入孵条件，建议完善后重新提交"

# Global instance
deepseek_client = DeepSeekClient()