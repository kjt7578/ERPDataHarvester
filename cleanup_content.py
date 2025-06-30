#!/usr/bin/env python3
"""
Content 폴더 정리 스크립트
logs 폴더를 제외한 모든 다운로드된 파일들을 안전하게 삭제합니다.
"""
import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContentCleaner:
    """Content 폴더 정리 클래스"""
    
    def __init__(self, content_dir: str = "./Content"):
        """
        초기화
        
        Args:
            content_dir: Content 폴더 경로
        """
        self.content_dir = Path(content_dir)
        self.logs_dir = self.content_dir / "logs"
        
        # 삭제 대상 폴더들 (logs 제외)
        self.target_dirs = [
            "Resume",
            "case", 
            "client",
            "JD",
            "metadata",
            "results"
        ]
        
        # 삭제 통계
        self.stats = {
            'files_deleted': 0,
            'dirs_deleted': 0,
            'total_size_mb': 0.0,
            'errors': []
        }
        
    def scan_content(self) -> Dict[str, List[Path]]:
        """
        Content 폴더 스캔하여 삭제 대상 파일/폴더 목록 생성
        
        Returns:
            삭제 대상 파일/폴더 목록
        """
        targets = {
            'files': [],
            'dirs': []
        }
        
        if not self.content_dir.exists():
            logger.warning(f"Content 디렉토리가 존재하지 않습니다: {self.content_dir}")
            return targets
            
        logger.info(f"Content 디렉토리 스캔 중: {self.content_dir}")
        
        # 각 대상 폴더 스캔
        for dir_name in self.target_dirs:
            dir_path = self.content_dir / dir_name
            if dir_path.exists():
                logger.info(f"스캔 중: {dir_name}/")
                
                # 폴더 내 모든 파일과 하위 폴더 수집
                for item in dir_path.rglob("*"):
                    if item.is_file():
                        targets['files'].append(item)
                    elif item.is_dir():
                        # 빈 폴더만 추가 (파일이 있는 폴더는 파일 삭제 후 자동으로 삭제됨)
                        if not any(item.iterdir()):
                            targets['dirs'].append(item)
                            
        # results 폴더의 파일들도 추가
        results_dir = self.content_dir / "results"
        if results_dir.exists():
            for item in results_dir.iterdir():
                if item.is_file():
                    targets['files'].append(item)
                    
        return targets
        
    def calculate_size(self, file_paths: List[Path]) -> float:
        """
        파일들의 총 크기 계산 (MB)
        
        Args:
            file_paths: 파일 경로 목록
            
        Returns:
            총 크기 (MB)
        """
        total_size = 0.0
        for file_path in file_paths:
            try:
                if file_path.exists():
                    total_size += file_path.stat().st_size
            except Exception as e:
                logger.warning(f"파일 크기 계산 실패: {file_path} - {e}")
                
        return total_size / (1024 * 1024)  # MB로 변환
        
    def display_targets(self, targets: Dict[str, List[Path]]) -> None:
        """
        삭제 대상 파일/폴더 목록 표시
        
        Args:
            targets: 삭제 대상 목록
        """
        print("\n" + "="*60)
        print("🗑️  삭제 대상 파일/폴더 목록")
        print("="*60)
        
        if not targets['files'] and not targets['dirs']:
            print("✅ 삭제할 파일/폴더가 없습니다.")
            return
            
        # 파일 목록 표시
        if targets['files']:
            print(f"\n📄 파일 ({len(targets['files'])}개):")
            for file_path in sorted(targets['files']):
                try:
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    print(f"   {file_path.relative_to(self.content_dir)} ({size_mb:.2f} MB)")
                except Exception as e:
                    print(f"   {file_path.relative_to(self.content_dir)} (크기 계산 실패)")
                    
        # 폴더 목록 표시
        if targets['dirs']:
            print(f"\n📁 빈 폴더 ({len(targets['dirs'])}개):")
            for dir_path in sorted(targets['dirs']):
                print(f"   {dir_path.relative_to(self.content_dir)}/")
                
        # 총 크기 표시
        total_size = self.calculate_size(targets['files'])
        print(f"\n📊 총 크기: {total_size:.2f} MB")
        
    def confirm_deletion(self) -> bool:
        """
        삭제 확인
        
        Returns:
            사용자 확인 여부
        """
        print("\n" + "="*60)
        print("⚠️  주의: 이 작업은 되돌릴 수 없습니다!")
        print("="*60)
        print("다음 폴더들이 삭제됩니다:")
        for dir_name in self.target_dirs:
            print(f"   - {dir_name}/")
        print("\nlogs/ 폴더는 보존됩니다.")
        
        while True:
            response = input("\n정말 삭제하시겠습니까? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                print("'yes' 또는 'no'로 답변해주세요.")
                
    def safe_delete_file(self, file_path: Path) -> bool:
        """
        파일 안전 삭제
        
        Args:
            file_path: 삭제할 파일 경로
            
        Returns:
            삭제 성공 여부
        """
        try:
            if file_path.exists():
                # 파일 크기 계산
                size_mb = file_path.stat().st_size / (1024 * 1024)
                
                # 파일 삭제
                file_path.unlink()
                
                self.stats['files_deleted'] += 1
                self.stats['total_size_mb'] += size_mb
                
                logger.debug(f"파일 삭제됨: {file_path}")
                return True
        except Exception as e:
            error_msg = f"파일 삭제 실패: {file_path} - {e}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return False
            
    def safe_delete_dir(self, dir_path: Path) -> bool:
        """
        폴더 안전 삭제
        
        Args:
            dir_path: 삭제할 폴더 경로
            
        Returns:
            삭제 성공 여부
        """
        try:
            if dir_path.exists():
                # 폴더 삭제
                dir_path.rmdir()
                
                self.stats['dirs_deleted'] += 1
                logger.debug(f"폴더 삭제됨: {dir_path}")
                return True
        except Exception as e:
            error_msg = f"폴더 삭제 실패: {dir_path} - {e}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return False
            
    def cleanup(self, dry_run: bool = False) -> bool:
        """
        Content 폴더 정리 실행
        
        Args:
            dry_run: 실제 삭제하지 않고 시뮬레이션만 실행
            
        Returns:
            정리 성공 여부
        """
        logger.info("Content 폴더 정리 시작")
        
        # 삭제 대상 스캔
        targets = self.scan_content()
        
        if not targets['files'] and not targets['dirs']:
            logger.info("삭제할 파일/폴더가 없습니다.")
            return True
            
        # 삭제 대상 표시
        self.display_targets(targets)
        
        if dry_run:
            print("\n🔍 DRY RUN 모드: 실제 삭제는 수행되지 않습니다.")
            return True
            
        # 사용자 확인
        if not self.confirm_deletion():
            logger.info("사용자가 삭제를 취소했습니다.")
            return False
            
        # 삭제 실행
        logger.info("파일/폴더 삭제 시작...")
        
        # 파일 삭제
        for file_path in targets['files']:
            if not self.safe_delete_file(file_path):
                logger.warning(f"파일 삭제 실패: {file_path}")
                
        # 빈 폴더 삭제
        for dir_path in targets['dirs']:
            if not self.safe_delete_dir(dir_path):
                logger.warning(f"폴더 삭제 실패: {dir_path}")
                
        # 상위 빈 폴더들도 삭제
        self._cleanup_empty_dirs()
        
        # 결과 리포트
        self._print_report()
        
        return True
        
    def _cleanup_empty_dirs(self) -> None:
        """빈 폴더들을 재귀적으로 삭제"""
        for dir_name in self.target_dirs:
            dir_path = self.content_dir / dir_name
            if dir_path.exists():
                try:
                    # 폴더가 비어있으면 삭제
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        self.stats['dirs_deleted'] += 1
                        logger.debug(f"빈 폴더 삭제됨: {dir_path}")
                except Exception as e:
                    logger.warning(f"빈 폴더 삭제 실패: {dir_path} - {e}")
                    
    def _print_report(self) -> None:
        """정리 결과 리포트 출력"""
        print("\n" + "="*60)
        print("📊 정리 완료 리포트")
        print("="*60)
        print(f"삭제된 파일: {self.stats['files_deleted']}개")
        print(f"삭제된 폴더: {self.stats['dirs_deleted']}개")
        print(f"총 삭제된 크기: {self.stats['total_size_mb']:.2f} MB")
        
        if self.stats['errors']:
            print(f"\n❌ 오류 발생: {len(self.stats['errors'])}개")
            for error in self.stats['errors']:
                print(f"   - {error}")
        else:
            print("\n✅ 모든 작업이 성공적으로 완료되었습니다.")
            
        print(f"\n📁 logs 폴더는 보존되었습니다: {self.logs_dir}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Content 폴더 정리 스크립트 - logs 폴더를 제외한 모든 파일 삭제"
    )
    parser.add_argument(
        '--content-dir', 
        default='./Content',
        help='Content 폴더 경로 (기본값: ./Content)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 삭제하지 않고 시뮬레이션만 실행'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='확인 절차 없이 바로 삭제 (주의: 위험함)'
    )
    
    args = parser.parse_args()
    
    # ContentCleaner 초기화
    cleaner = ContentCleaner(args.content_dir)
    
    if args.dry_run:
        print("🔍 DRY RUN 모드로 실행합니다.")
        cleaner.cleanup(dry_run=True)
    elif args.force:
        print("⚠️  FORCE 모드로 실행합니다. 확인 절차를 건너뜁니다.")
        targets = cleaner.scan_content()
        cleaner.display_targets(targets)
        cleaner.cleanup(dry_run=False)
    else:
        # 일반 모드
        cleaner.cleanup(dry_run=False)


if __name__ == "__main__":
    main()
