# 日历同步集成指南

## 支持的日历平台

| 平台 | 协议 | 状态 |
|-----|------|------|
| Google Calendar | API v3 | ✅ 支持 |
| Outlook/Microsoft 365 | Graph API | ✅ 支持 |
| Apple iCloud | CalDAV | ✅ 支持 |
| 本地日历 | ICS文件 | ✅ 支持 |

## 快速集成

### Google Calendar

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime

class GoogleCalendarSync:
    def __init__(self, credentials):
        self.service = build('calendar', 'v3', credentials=credentials)
    
    def add_event(self, event):
        """添加事件到Google日历"""
        body = {
            'summary': event['name'],
            'start': {
                'dateTime': event['start'],
                'timeZone': 'Asia/Shanghai',
            },
            'end': {
                'dateTime': event['end'],
                'timeZone': 'Asia/Shanghai',
            },
            'location': event.get('location', ''),
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 15},
                ],
            },
        }
        
        result = self.service.events().insert(
            calendarId='primary',
            body=body
        ).execute()
        return result['id']
    
    def sync_schedule(self, schedule):
        """同步整个排程"""
        for event in schedule:
            try:
                event_id = self.add_event(event)
                print(f"✅ 已同步: {event['name']}")
            except Exception as e:
                print(f"❌ 同步失败 {event['name']}: {e}")
```

### Outlook/Microsoft 365

```python
import requests

class OutlookCalendarSync:
    def __init__(self, access_token):
        self.token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0"
    
    def add_event(self, event):
        """添加事件到Outlook日历"""
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        body = {
            "subject": event['name'],
            "start": {
                "dateTime": event['start'],
                "timeZone": "China Standard Time"
            },
            "end": {
                "dateTime": event['end'],
                "timeZone": "China Standard Time"
            },
            "location": {
                "displayName": event.get('location', '')
            }
        }
        
        response = requests.post(
            f"{self.base_url}/me/events",
            headers=headers,
            json=body
        )
        return response.json()
```

### Apple iCloud (CalDAV)

```python
import caldav

class AppleCalendarSync:
    def __init__(self, username, password):
        self.client = caldav.DAVClient(
            url="https://caldav.icloud.com/",
            username=username,
            password=password
        )
        self.principal = self.client.principal()
    
    def add_event(self, event, calendar_name="学习"):
        """添加事件到Apple日历"""
        # 获取或创建日历
        calendars = self.principal.calendars()
        calendar = None
        for cal in calendars:
            if cal.name == calendar_name:
                calendar = cal
                break
        
        if not calendar:
            calendar = self.principal.make_calendar(name=calendar_name)
        
        # 创建事件
        ics_data = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Smart Study Scheduler//CN
BEGIN:VEVENT
SUMMARY:{event['name']}
DTSTART:{event['start'].replace('-', '').replace(':', '')}
DTEND:{event['end'].replace('-', '').replace(':', '')}
LOCATION:{event.get('location', '')}
END:VEVENT
END:VCALENDAR"""
        
        calendar.add_event(ics_data)
```

### 本地ICS文件

```python
from icalendar import Calendar, Event
import pytz

class LocalCalendarSync:
    def generate_ics(self, schedule, output_path):
        """生成ICS日历文件"""
        cal = Calendar()
        cal.add('prodid', '-//Smart Study Scheduler//CN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        
        for item in schedule:
            event = Event()
            event.add('summary', item['name'])
            event.add('dtstart', item['start'])
            event.add('dtend', item['end'])
            
            if item.get('location'):
                event.add('location', item['location'])
            
            if item.get('description'):
                event.add('description', item['description'])
            
            # 添加提醒
            from icalendar import vAlarm
            alarm = vAlarm()
            alarm.add('action', 'DISPLAY')
            alarm.add('trigger', item['start'] - timedelta(minutes=15))
            alarm.add('description', f'提醒: {item["name"]}')
            event.add_component(alarm)
            
            cal.add_component(event)
        
        with open(output_path, 'wb') as f:
            f.write(cal.to_ical())
        
        return output_path
```

## 认证流程

### Google OAuth 2.0

```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_google_credentials():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    return creds
```

### Microsoft OAuth 2.0

```python
import msal

def get_microsoft_token():
    app = msal.PublicClientApplication(
        "your-client-id",
        authority="https://login.microsoftonline.com/common"
    )
    
    result = app.acquire_token_interactive(
        scopes=["Calendars.ReadWrite"]
    )
    
    return result['access_token']
```

## 同步策略

### 增量同步

```python
def sync_incremental(calendar_api, schedule, last_sync):
    """增量同步，只更新变更"""
    # 获取日历中上次同步后的事件
    existing_events = calendar_api.get_events(since=last_sync)
    
    for event in schedule:
        # 检查是否存在
        existing = find_existing(existing_events, event)
        
        if existing:
            # 更新
            if event_modified(event, existing):
                calendar_api.update_event(existing['id'], event)
        else:
            # 新建
            calendar_api.add_event(event)
    
    # 删除已取消的事件
    for existing in existing_events:
        if not find_in_schedule(schedule, existing):
            calendar_api.delete_event(existing['id'])
```

### 双向同步

```python
def bidirectional_sync(local_schedule, calendar_api, strategy="local_wins"):
    """
    双向同步策略
    
    strategy:
        - local_wins: 本地优先
        - remote_wins: 远程优先
        - merge: 合并冲突（手动选择）
    """
    remote_events = calendar_api.get_events()
    
    conflicts = detect_conflicts(local_schedule, remote_events)
    
    for conflict in conflicts:
        if strategy == "local_wins":
            calendar_api.update_event(conflict['remote_id'], conflict['local'])
        elif strategy == "remote_wins":
            update_local_schedule(conflict['local_id'], conflict['remote'])
        else:
            # 标记冲突待人工处理
            mark_conflict(conflict)
```

## 错误处理

```python
class CalendarSyncError(Exception):
    pass

def robust_sync(calendar_api, schedule, max_retries=3):
    """健壮的同步函数"""
    failed = []
    
    for event in schedule:
        for attempt in range(max_retries):
            try:
                calendar_api.add_event(event)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    failed.append({
                        'event': event,
                        'error': str(e)
                    })
                else:
                    time.sleep(2 ** attempt)  # 指数退避
    
    if failed:
        print(f"同步完成，{len(failed)}个事件失败")
        save_failed_events(failed)
    
    return failed
```

## 使用示例

```python
# 完整同步流程
from smart_study_scheduler import SmartScheduler

# 1. 生成排程
scheduler = SmartScheduler(preferences)
schedule = scheduler.generate_schedule(courses, tasks, week_start)

# 2. 同步到Google日历
google_creds = get_google_credentials()
google_sync = GoogleCalendarSync(google_creds)
google_sync.sync_schedule(schedule)

# 3. 导出本地ICS
local_sync = LocalCalendarSync()
local_sync.generate_ics(schedule, "study_schedule.ics")

print("✅ 同步完成！")
```

## 平台限制

| 平台 | 限制说明 |
|-----|---------|
| Google | 每秒10次请求，每日100万次 |
| Outlook | 每秒4次请求，每日10000次 |
| Apple | 需应用专用密码 |
